from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from litigation_planner.publication_contract import load_publication_contract


class SemanticRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class Dimension:
    id: str
    expression: str
    column: str
    cube_field: str
    type: str
    operators: tuple[str, ...]
    label: str
    format: str
    definition: str
    tooltip: str
    export_label: str


@dataclass(frozen=True)
class Measure:
    id: str
    label: str
    format: str
    unit: str
    definition: str
    tooltip: str
    limitation: str
    export_label: str


@dataclass(frozen=True)
class Context:
    id: str
    label: str
    predicate: str
    dimensions: tuple[str, ...]
    measures: tuple[str, ...]
    support_measure: str
    minimum_support: int
    cube_collection: str
    reconciliation_dimensions: tuple[str, ...]
    reconciliation_groupings: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Binding:
    context: str
    measure: str
    numerator: str
    denominator: str
    cube_fields: tuple[str, ...]
    cube_numerator_field: str
    cube_denominator_field: str


@dataclass(frozen=True)
class SemanticRegistry:
    version: int
    registry_id: str
    dataset_version: str
    schema_version: str
    default_query_rows: int
    maximum_query_rows: int
    dimensions: tuple[Dimension, ...]
    measures: tuple[Measure, ...]
    contexts: tuple[Context, ...]
    bindings: tuple[Binding, ...]

    @property
    def dimension_by_id(self) -> dict[str, Dimension]:
        return {item.id: item for item in self.dimensions}

    @property
    def measure_by_id(self) -> dict[str, Measure]:
        return {item.id: item for item in self.measures}

    @property
    def context_by_id(self) -> dict[str, Context]:
        return {item.id: item for item in self.contexts}

    @property
    def binding_by_key(self) -> dict[tuple[str, str], Binding]:
        return {(item.context, item.measure): item for item in self.bindings}


@dataclass(frozen=True)
class QueryFilter:
    dimension: str
    operator: str
    value: object


@dataclass(frozen=True)
class CompiledQuery:
    sql: str
    parameters: tuple[object, ...]


_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")
_FORMATS = {"boolean", "category", "code", "days_1", "integer", "month", "percent_1", "year"}
_TYPES = {"boolean", "date", "integer", "string"}
_OPERATORS = {"eq", "in", "between"}
_PREDICATES = {"all": "true", "pending": "pending_status"}
_DERIVED_DIMENSIONS = {
    "filing_year": "cast(extract(year from filed_month) as bigint)",
    "age_band": "case when duration_days < 365 then 'under_1_year' "
    "when duration_days < 730 then '1_to_2_years' "
    "when duration_days < 1825 then '2_to_5_years' else '5_years_or_more' end",
}
_AGGREGATIONS = {
    "rows": "count(*)",
    "canonical_rows": "count_if(identity_quality_status = 'canonical')",
    "pending_rows": "count_if(pending_status)",
    "terminated_rows": "count_if(event_observed)",
    "matched_rows": "count_if(recap_match_available)",
    "supported_nature_rows": "count_if(nature_of_suit_mapping_status = 'supported')",
    "duration_days": "sum(duration_days)",
    "observed_duration_days": "sum(case when event_observed then duration_days else 0 end)",
}


def _items(document: dict[str, Any], name: str, kind: type) -> tuple[Any, ...]:
    try:
        values = tuple(kind(**item) for item in document[name])
    except (KeyError, TypeError) as error:
        raise SemanticRegistryError(f"invalid {name} registry entries") from error
    if not values:
        raise SemanticRegistryError(f"registry requires {name}")
    return values


def _unique_ids(items: Sequence[Any], name: str) -> None:
    ids = [item.id for item in items]
    if any(not _IDENTIFIER.fullmatch(value) for value in ids) or len(ids) != len(set(ids)):
        raise SemanticRegistryError(f"{name} identifiers must be unique and allowlisted")


def load_semantic_registry(
    path: Path = Path("config/semantic-metrics-v1.toml"),
    contract_path: Path = Path("config/public-row-mart-v1.toml"),
) -> SemanticRegistry:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    dimensions = tuple(
        Dimension(**{**item, "operators": tuple(item["operators"])})
        for item in document.get("dimension", ())
    )
    measures = _items(document, "measure", Measure)
    contexts = tuple(
        Context(
            **{
                **item,
                "dimensions": tuple(item["dimensions"]),
                "measures": tuple(item["measures"]),
                "reconciliation_dimensions": tuple(item["reconciliation_dimensions"]),
                "reconciliation_groupings": tuple(
                    tuple(grouping) for grouping in item["reconciliation_groupings"]
                ),
            }
        )
        for item in document.get("context", ())
    )
    bindings = tuple(
        Binding(**{**item, "cube_fields": tuple(item["cube_fields"])})
        for item in document.get("binding", ())
    )
    registry = SemanticRegistry(
        version=document.get("version"),
        registry_id=document.get("registry_id"),
        dataset_version=document.get("dataset_version"),
        schema_version=document.get("schema_version"),
        default_query_rows=document.get("default_query_rows"),
        maximum_query_rows=document.get("maximum_query_rows"),
        dimensions=dimensions,
        measures=measures,
        contexts=contexts,
        bindings=bindings,
    )
    _validate_registry(registry, contract_path)
    return registry


def _validate_registry(registry: SemanticRegistry, contract_path: Path) -> None:
    contract = load_publication_contract(contract_path)
    if (
        registry.version != 1
        or registry.registry_id != "metrics.v1"
        or registry.dataset_version != contract.dataset_version
        or registry.schema_version != contract.schema_version
    ):
        raise SemanticRegistryError("semantic registry is incompatible with publication contract")
    if not (
        0
        < registry.default_query_rows
        <= registry.maximum_query_rows
        <= contract.maximum_query_rows
    ):
        raise SemanticRegistryError("semantic query bounds are invalid")
    _unique_ids(registry.dimensions, "dimension")
    _unique_ids(registry.measures, "measure")
    _unique_ids(registry.contexts, "context")
    if not registry.bindings:
        raise SemanticRegistryError("registry requires measure bindings")

    allowed_columns = set(contract.allowed_fields)
    for dimension in registry.dimensions:
        if (
            dimension.expression not in {"column", *_DERIVED_DIMENSIONS}
            or dimension.column not in allowed_columns
            or dimension.type not in _TYPES
            or dimension.format not in _FORMATS
            or not dimension.operators
            or not set(dimension.operators) <= _OPERATORS
            or not all(
                (
                    dimension.cube_field,
                    dimension.label,
                    dimension.definition,
                    dimension.tooltip,
                    dimension.export_label,
                )
            )
        ):
            raise SemanticRegistryError(f"dimension is incomplete or unsafe: {dimension.id}")
        if dimension.expression == "column" and dimension.column != dimension.id:
            raise SemanticRegistryError(f"direct dimension column must match id: {dimension.id}")
    for measure in registry.measures:
        if measure.format not in _FORMATS or not all(
            (
                measure.label,
                measure.unit,
                measure.definition,
                measure.tooltip,
                measure.limitation,
                measure.export_label,
            )
        ):
            raise SemanticRegistryError(f"measure metadata is incomplete: {measure.id}")

    dimensions = registry.dimension_by_id
    measures = registry.measure_by_id
    contexts = registry.context_by_id
    for context in registry.contexts:
        if (
            context.predicate not in _PREDICATES
            or not context.dimensions
            or not context.measures
            or not set(context.dimensions) <= dimensions.keys()
            or not set(context.measures) <= measures.keys()
            or context.support_measure not in context.measures
            or context.minimum_support <= 0
            or not context.cube_collection
            or not set(context.reconciliation_dimensions) <= set(context.dimensions)
            or not context.reconciliation_groupings
            or any(
                not set(grouping) <= set(context.reconciliation_dimensions)
                for grouping in context.reconciliation_groupings
            )
        ):
            raise SemanticRegistryError(f"context is incomplete or incompatible: {context.id}")

    binding_keys = [(item.context, item.measure) for item in registry.bindings]
    required_keys = {
        (context.id, measure) for context in registry.contexts for measure in context.measures
    }
    if len(binding_keys) != len(set(binding_keys)) or set(binding_keys) != required_keys:
        raise SemanticRegistryError(
            "measure bindings must cover every context measure exactly once"
        )
    cube_fields: dict[str, set[str]] = {context.id: set() for context in registry.contexts}
    for binding in registry.bindings:
        context = contexts.get(binding.context)
        if (
            context is None
            or binding.measure not in context.measures
            or binding.numerator not in _AGGREGATIONS
            or (binding.denominator and binding.denominator not in _AGGREGATIONS)
            or not binding.cube_fields
            or not binding.cube_numerator_field
            and not binding.denominator
            or binding.denominator
            and not binding.cube_denominator_field
            or cube_fields[binding.context] & set(binding.cube_fields)
        ):
            raise SemanticRegistryError(
                f"measure binding is incomplete or unsafe: {binding.context}.{binding.measure}"
            )
        cube_fields[binding.context].update(binding.cube_fields)


def _dimension_sql(dimension: Dimension) -> str:
    if dimension.expression == "column":
        return f'"{dimension.column}"'
    return _DERIVED_DIMENSIONS[dimension.expression]


def _measure_sql(binding: Binding) -> str:
    numerator = _AGGREGATIONS[binding.numerator]
    if not binding.denominator:
        return numerator
    denominator = _AGGREGATIONS[binding.denominator]
    return f"cast(({numerator}) as double) / nullif(({denominator}), 0)"


def _normalize_value(value: object, expected_type: str) -> object:
    if expected_type == "boolean" and isinstance(value, bool):
        return value
    if expected_type == "integer" and isinstance(value, int) and not isinstance(value, bool):
        return value
    if expected_type == "string" and isinstance(value, str) and value:
        return value
    if expected_type == "date":
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            try:
                return date.fromisoformat(value).isoformat()
            except ValueError:
                pass
    raise SemanticRegistryError(f"filter value does not match {expected_type}")


def _filter_sql(query_filter: QueryFilter, dimension: Dimension) -> tuple[str, tuple[object, ...]]:
    if query_filter.operator not in dimension.operators:
        raise SemanticRegistryError(
            f"operator is not allowed for {query_filter.dimension}: {query_filter.operator}"
        )
    expression = _dimension_sql(dimension)
    if query_filter.operator == "eq":
        return f"{expression} = ?", (_normalize_value(query_filter.value, dimension.type),)
    if not isinstance(query_filter.value, Sequence) or isinstance(query_filter.value, str):
        raise SemanticRegistryError("multi-value filter requires a sequence")
    values = tuple(query_filter.value)
    if query_filter.operator == "between":
        if len(values) != 2:
            raise SemanticRegistryError("between filter requires exactly two values")
        normalized = tuple(_normalize_value(value, dimension.type) for value in values)
        return f"{expression} between ? and ?", normalized
    if not 0 < len(values) <= 100:
        raise SemanticRegistryError("in filter requires between 1 and 100 values")
    normalized = tuple(_normalize_value(value, dimension.type) for value in values)
    return f"{expression} in ({','.join('?' for _ in normalized)})", normalized


def compile_query(
    registry: SemanticRegistry,
    *,
    context_id: str,
    measure_ids: Sequence[str],
    dimension_ids: Sequence[str] = (),
    filters: Sequence[QueryFilter] = (),
    order_by: Sequence[tuple[str, str]] = (),
    limit: int | None = None,
    include_reconciliation_terms: bool = False,
) -> CompiledQuery:
    context = registry.context_by_id.get(context_id)
    if context is None:
        raise SemanticRegistryError(f"unknown context: {context_id}")
    if not measure_ids or len(measure_ids) != len(set(measure_ids)):
        raise SemanticRegistryError("query requires unique registered measures")
    if len(dimension_ids) != len(set(dimension_ids)):
        raise SemanticRegistryError("query dimensions must be unique")
    if not set(measure_ids) <= set(context.measures):
        raise SemanticRegistryError("query contains a measure incompatible with its context")
    if not set(dimension_ids) <= set(context.dimensions):
        raise SemanticRegistryError("query contains a dimension incompatible with its context")

    row_limit = registry.default_query_rows if limit is None else limit
    if (
        isinstance(row_limit, bool)
        or not isinstance(row_limit, int)
        or not (0 < row_limit <= registry.maximum_query_rows)
    ):
        raise SemanticRegistryError("query limit is outside the registry bound")

    dimensions = registry.dimension_by_id
    bindings = registry.binding_by_key
    selections = [
        f'{_dimension_sql(dimensions[dimension_id])} as "{dimension_id}"'
        for dimension_id in dimension_ids
    ]
    for measure_id in measure_ids:
        binding = bindings[(context_id, measure_id)]
        selections.append(f'{_measure_sql(binding)} as "{measure_id}"')
        if include_reconciliation_terms:
            selections.append(f'{_AGGREGATIONS[binding.numerator]} as "__{measure_id}_numerator"')
            if binding.denominator:
                selections.append(
                    f'{_AGGREGATIONS[binding.denominator]} as "__{measure_id}_denominator"'
                )

    clauses = [_PREDICATES[context.predicate]]
    parameters: list[object] = []
    for query_filter in filters:
        if query_filter.dimension not in context.dimensions:
            raise SemanticRegistryError("filter dimension is incompatible with its context")
        clause, values = _filter_sql(query_filter, dimensions[query_filter.dimension])
        clauses.append(clause)
        parameters.extend(values)

    sql = f"select {', '.join(selections)} from row_mart where {' and '.join(clauses)}"
    if dimension_ids:
        sql += " group by " + ", ".join(
            _dimension_sql(dimensions[dimension_id]) for dimension_id in dimension_ids
        )
    support = bindings[(context_id, context.support_measure)]
    sql += f" having {_AGGREGATIONS[support.numerator]} >= {context.minimum_support}"

    selected = {*dimension_ids, *measure_ids}
    ordering = tuple(order_by) or tuple((dimension_id, "asc") for dimension_id in dimension_ids)
    if ordering:
        for identifier, direction in ordering:
            if identifier not in selected or direction.lower() not in {"asc", "desc"}:
                raise SemanticRegistryError("query order must reference selected registered fields")
        sql += " order by " + ", ".join(
            f'"{identifier}" {direction.lower()}' for identifier, direction in ordering
        )
    sql += f" limit {row_limit}"
    return CompiledQuery(sql=sql, parameters=tuple(parameters))


def compiled_registry_document(registry: SemanticRegistry) -> dict[str, object]:
    return {
        "version": registry.version,
        "registry_id": registry.registry_id,
        "dataset_version": registry.dataset_version,
        "schema_version": registry.schema_version,
        "default_query_rows": registry.default_query_rows,
        "maximum_query_rows": registry.maximum_query_rows,
        "dimensions": [asdict(item) for item in registry.dimensions],
        "measures": [asdict(item) for item in registry.measures],
        "contexts": [asdict(item) for item in registry.contexts],
        "bindings": [asdict(item) for item in registry.bindings],
    }


def render_compiled_registry(registry: SemanticRegistry) -> str:
    return (
        json.dumps(
            compiled_registry_document(registry),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def render_metric_definitions(registry: SemanticRegistry) -> str:
    lines = [
        "# Semantic metrics",
        "",
        (
            f"Registry `{registry.registry_id}` is the semantic source for labels, formulas, formats, "
            "tooltips, support rules, definitions, and exports."
        ),
        "",
        "| Measure | Definition | Format | Limitation | Export label |",
        "| --- | --- | --- | --- | --- |",
    ]
    for measure in registry.measures:
        values = (
            measure.label,
            measure.definition,
            measure.format,
            measure.limitation,
            measure.export_label,
        )
        lines.append("| " + " | ".join(value.replace("|", "\\|") for value in values) + " |")
    lines.extend(
        [
            "",
            "## Query contexts",
            "",
            "| Context | Measures | Compatible dimensions | Support rule |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for context in registry.contexts:
        lines.append(
            f"| {context.label} | {len(context.measures)} | {len(context.dimensions)} | "
            f"At least {context.minimum_support} {context.support_measure.replace('_', ' ')} |"
        )
    lines.extend(
        [
            "",
            (
                "Queries accept registered identifiers and operators only. Values use bound "
                "parameters, results are capped at 10,000 rows, and raw SQL is not accepted from "
                "URL or user input."
            ),
            "",
            (
                "Historical measures remain descriptive. Duration and age measures are not "
                "forecasts, and statistical records are not guaranteed unique legal cases."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _records(connection: duckdb.DuckDBPyConnection, query: CompiledQuery) -> list[dict[str, Any]]:
    cursor = connection.execute(query.sql, list(query.parameters))
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _cube_rows_for_grouping(
    rows: Sequence[Mapping[str, Any]],
    context: Context,
    dimensions: Mapping[str, Dimension],
    grouping: Sequence[str],
) -> list[Mapping[str, Any]]:
    ungrouped = set(context.reconciliation_dimensions) - set(grouping)
    return [
        row
        for row in rows
        if all(row[dimensions[identifier].cube_field] is not None for identifier in grouping)
        and all(row[dimensions[identifier].cube_field] is None for identifier in ungrouped)
    ]


def evaluate_semantic_registry(
    connection: duckdb.DuckDBPyConnection,
    registry: SemanticRegistry,
    approved_cube: Mapping[str, Any],
) -> dict[str, object]:
    dimensions = registry.dimension_by_id
    bindings = registry.binding_by_key
    expected_fields = 0
    mapped_fields = 0
    query_count = 0
    slice_count = 0
    comparison_count = 0
    maximum_difference = 0
    display_difference = 0.0

    for context in registry.contexts:
        cube_rows = approved_cube[context.cube_collection]
        dimension_fields = {
            dimensions[identifier].cube_field for identifier in context.reconciliation_dimensions
        }
        surface_fields = set(cube_rows[0]) - dimension_fields
        mapped = {
            field
            for measure_id in context.measures
            for field in bindings[(context.id, measure_id)].cube_fields
        }
        if mapped != surface_fields:
            raise SemanticRegistryError(f"cube measure coverage differs for {context.id}")
        expected_fields += len(surface_fields)
        mapped_fields += len(mapped)

        for grouping in context.reconciliation_groupings:
            query = compile_query(
                registry,
                context_id=context.id,
                measure_ids=context.measures,
                dimension_ids=grouping,
                limit=registry.maximum_query_rows,
                include_reconciliation_terms=True,
            )
            actual_rows = _records(connection, query)
            expected_rows = _cube_rows_for_grouping(cube_rows, context, dimensions, grouping)
            actual_by_key = {
                tuple(row[identifier] for identifier in grouping): row for row in actual_rows
            }
            expected_by_key = {
                tuple(row[dimensions[identifier].cube_field] for identifier in grouping): row
                for row in expected_rows
            }
            if actual_by_key.keys() != expected_by_key.keys():
                raise SemanticRegistryError(
                    f"semantic slice keys differ for {context.id}:{','.join(grouping)}"
                )
            query_count += 1
            slice_count += len(actual_rows)

            for key, actual in actual_by_key.items():
                expected = expected_by_key[key]
                for measure_id in context.measures:
                    binding = bindings[(context.id, measure_id)]
                    numerator = actual[f"__{measure_id}_numerator"]
                    if not binding.denominator:
                        for cube_field in binding.cube_fields:
                            difference = abs(numerator - expected[cube_field])
                            maximum_difference = max(maximum_difference, difference)
                            comparison_count += 1
                        continue

                    denominator = actual[f"__{measure_id}_denominator"]
                    expected_denominator = expected[binding.cube_denominator_field]
                    if binding.cube_numerator_field:
                        expected_numerator = expected[binding.cube_numerator_field]
                    else:
                        expected_numerator = round(
                            expected[binding.cube_fields[0]] * expected_denominator
                        )
                    maximum_difference = max(
                        maximum_difference,
                        abs(numerator - expected_numerator),
                        abs(denominator - expected_denominator),
                    )
                    display_difference = max(
                        display_difference,
                        abs(float(actual[measure_id]) - float(expected[binding.cube_fields[0]])),
                    )
                    comparison_count += 2

    measure_ids = {binding.measure for binding in registry.bindings}
    coverage = len(measure_ids) / len(registry.measures)
    cube_field_coverage = mapped_fields / expected_fields
    if coverage != 1.0 or cube_field_coverage != 1.0 or maximum_difference != 0:
        raise SemanticRegistryError("semantic registry failed coverage or reconciliation")
    return {
        "semantic_metric_registry_coverage": coverage,
        "semantic_metric_reconciliation_error": float(maximum_difference),
        "cube_field_coverage": cube_field_coverage,
        "registered_measures": len(registry.measures),
        "registered_dimensions": len(registry.dimensions),
        "registered_contexts": len(registry.contexts),
        "measure_bindings": len(registry.bindings),
        "mapped_cube_measure_fields": mapped_fields,
        "queries": query_count,
        "slices": slice_count,
        "exact_comparisons": comparison_count,
        "display_float_max_abs_difference": display_difference,
    }
