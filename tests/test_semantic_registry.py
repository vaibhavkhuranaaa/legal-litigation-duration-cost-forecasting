import json
from pathlib import Path

import duckdb
import pytest

from litigation_planner.semantic_registry import (
    QueryFilter,
    SemanticRegistryError,
    _cube_rows_for_grouping,
    compile_query,
    load_semantic_registry,
    render_compiled_registry,
    render_metric_definitions,
)

REGISTRY_PATH = Path("config/semantic-metrics-v1.toml")
CUBE_PATH = Path("frontend/src/full-population.v1.json")
COMPILED_PATH = Path("frontend/src/semantic-metrics.v1.json")
DEFINITIONS_PATH = Path("docs/semantic-metrics.md")


def registry():
    return load_semantic_registry(REGISTRY_PATH)


def test_registry_is_complete_versioned_and_canonical() -> None:
    semantic = registry()
    assert semantic.registry_id == "metrics.v1"
    assert semantic.dataset_version == "fjc-civil-2026-03-31.v1"
    assert len(semantic.measures) == 11
    assert len(semantic.dimensions) == 17
    assert len(semantic.contexts) == 3
    assert len(semantic.bindings) == 17
    assert COMPILED_PATH.read_text(encoding="utf-8") == render_compiled_registry(semantic)
    assert DEFINITIONS_PATH.read_text(encoding="utf-8") == render_metric_definitions(semantic)
    assert all(measure.label in DEFINITIONS_PATH.read_text() for measure in semantic.measures)


def test_registry_maps_every_aggregate_cube_measure_field_once() -> None:
    semantic = registry()
    cube = json.loads(CUBE_PATH.read_text(encoding="utf-8"))
    dimensions = semantic.dimension_by_id
    bindings = semantic.binding_by_key
    for context in semantic.contexts:
        dimension_fields = {
            dimensions[identifier].cube_field for identifier in context.reconciliation_dimensions
        }
        expected = set(cube[context.cube_collection][0]) - dimension_fields
        mapped = {
            field
            for measure_id in context.measures
            for field in bindings[(context.id, measure_id)].cube_fields
        }
        assert mapped == expected


def test_cube_grouping_selects_only_matching_grouping_set_rows() -> None:
    semantic = registry()
    context = semantic.context_by_id["portfolio"]
    rows = [
        {"district_code": "01", "nature_family": "civil_rights"},
        {"district_code": "01", "nature_family": None},
        {"district_code": None, "nature_family": "civil_rights"},
        {"district_code": None, "nature_family": None},
    ]
    selected = _cube_rows_for_grouping(
        rows,
        context,
        semantic.dimension_by_id,
        ("district_code", "nature_of_suit_family"),
    )
    assert selected == rows[:1]


def test_compiler_uses_allowlists_parameters_support_and_bounds() -> None:
    semantic = registry()
    query = compile_query(
        semantic,
        context_id="portfolio",
        measure_ids=("statistical_records", "pending_share"),
        dimension_ids=("district_code",),
        filters=(
            QueryFilter("district_code", "in", ("01", "02")),
            QueryFilter("filed_month", "between", ("2020-01-01", "2021-12-01")),
        ),
        order_by=(("statistical_records", "desc"),),
        limit=25,
    )
    assert query.parameters == ("01", "02", "2020-01-01", "2021-12-01")
    assert query.sql.count("?") == 4
    assert "count(*) >= 200" in query.sql
    assert 'order by "statistical_records" desc limit 25' in query.sql
    assert "2020-01-01" not in query.sql

    with pytest.raises(SemanticRegistryError, match="measure incompatible"):
        compile_query(
            semantic,
            context_id="portfolio",
            measure_ids=("average_age_days",),
        )
    with pytest.raises(SemanticRegistryError, match="unknown context"):
        compile_query(semantic, context_id="row_mart; drop table", measure_ids=("pending_records",))
    with pytest.raises(SemanticRegistryError, match="outside the registry bound"):
        compile_query(
            semantic,
            context_id="portfolio",
            measure_ids=("statistical_records",),
            limit=10_001,
        )
    with pytest.raises(SemanticRegistryError, match="operator is not allowed"):
        compile_query(
            semantic,
            context_id="portfolio",
            measure_ids=("statistical_records",),
            filters=(QueryFilter("district_code", "between", ("01", "99")),),
        )


def test_compiled_formulas_execute_with_exact_censoring_semantics() -> None:
    semantic = registry()
    connection = duckdb.connect()
    try:
        connection.execute(
            """
            create table row_mart as
            select
                '01'::varchar as district_code,
                'civil_rights'::varchar as nature_of_suit_family,
                (i % 4 = 0) as pending_status,
                not (i % 4 = 0) as event_observed,
                (i % 3 = 0) as recap_match_available,
                case when i % 10 = 0 then 'collision' else 'canonical' end::varchar
                    as identity_quality_status,
                'supported'::varchar as nature_of_suit_mapping_status,
                i::integer as duration_days
            from range(800) as rows(i)
            """
        )
        query = compile_query(
            semantic,
            context_id="portfolio",
            measure_ids=(
                "statistical_records",
                "pending_records",
                "terminated_records",
                "pending_share",
                "average_observed_duration_days",
            ),
            dimension_ids=("district_code",),
            limit=10,
            include_reconciliation_terms=True,
        )
        cursor = connection.execute(query.sql, list(query.parameters))
        columns = [description[0] for description in cursor.description]
        values = cursor.fetchone()
        row = dict(zip(columns, values, strict=True)) if values else None
    finally:
        connection.close()
    assert row is not None
    assert row["statistical_records"] == 800
    assert row["pending_records"] == 200
    assert row["terminated_records"] == 600
    assert row["pending_share"] == 0.25
    assert row["__statistical_records_numerator"] == 800
    assert row["__pending_share_numerator"] == 200
    assert row["__pending_share_denominator"] == 800
