from pathlib import Path

import pytest

from litigation_planner.publication_contract import (
    PublicationContractError,
    load_publication_contract,
)
from scripts.build_public_row_mart import (
    _exact_cube_projection,
    _manifest,
    _max_difference,
    build_mart,
    compare_candidates,
)

CONTRACT_PATH = Path("config/public-row-mart-v1.toml")


def test_full_manifest_is_deterministic_and_reconciles_all_annual_partitions() -> None:
    contract = load_publication_contract(CONTRACT_PATH)
    years = range(2010, 2027)
    base = contract.expected_statistical_records // len(years)
    partitions = [
        {
            "path": f"filing_year={year}/part-00000.parquet",
            "filing_year": year,
            "row_count": base,
            "byte_size": 1,
            "sha256": f"{year - 2010:064x}",
            "dataset_version": contract.dataset_version,
            "schema_version": contract.schema_version,
        }
        for year in years
    ]
    partitions[-1]["row_count"] += contract.expected_statistical_records - base * len(years)
    manifest = _manifest(
        contract,
        partitions,
        metric_registry_version="metrics.v1",
        minimum_app_version="2.0.0",
    )
    assert manifest["total_records"] == 5_008_334
    assert len(manifest["partitions"]) == 17


def test_replay_compares_complete_candidate_bytes(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        (root / "filing_year=2010").mkdir(parents=True)
        (root / "manifest.json").write_text("{}\n", encoding="utf-8")
        (root / "filing_year=2010/part-00000.parquet").write_bytes(b"PAR1fixture")
    assert compare_candidates(first, second) == {
        "identical": 1,
        "files_compared": 2,
        "differences": 0,
    }
    (second / "manifest.json").write_text('{"changed":true}\n', encoding="utf-8")
    with pytest.raises(PublicationContractError, match="bytes differ"):
        compare_candidates(first, second)


def test_cube_difference_fails_closed_on_structure_and_measures() -> None:
    assert _max_difference({"count": 3, "share": 0.25}, {"count": 3, "share": 0.25}) == 0
    assert _max_difference([1.0], [1.5]) == 0.5
    with pytest.raises(PublicationContractError, match="keys differ"):
        _max_difference({"count": 3}, {"other": 3})


def test_cube_projection_compares_exact_sufficient_statistics() -> None:
    cube = {
        "population": {"statistical_records": 2},
        "portfolio_slices": [
            {
                "observed_terminations": 2,
                "average_observed_duration_days": 1.5000000000000002,
                "match_coverage": 0.5,
                "pending_share": 0.0,
            }
        ],
        "filing_series": [],
        "pending_age_series": [{"pending_records": 2, "average_age_days": 10.499999999999998}],
        "nature_families": [],
        "filing_years": [],
        "district_codes": [],
    }
    projected = _exact_cube_projection(cube)
    assert projected["portfolio_slices"][0]["observed_duration_days"] == 3
    assert projected["pending_age_series"][0]["age_days"] == 21


def test_full_build_refuses_output_inside_public_repository(tmp_path: Path) -> None:
    with pytest.raises(PublicationContractError, match="outside tracked Git"):
        build_mart(
            warehouse=tmp_path / "missing.duckdb",
            output=Path("data/row-mart"),
            secret_path=tmp_path / "missing.key",
            contract_path=CONTRACT_PATH,
            approved_cube_path=Path("frontend/src/full-population.v1.json"),
        )
