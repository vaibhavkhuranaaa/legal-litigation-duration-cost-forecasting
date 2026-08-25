import json
from pathlib import Path

CUBE_PATH = Path("frontend/src/full-population.v1.json")


def load_cube() -> dict[str, object]:
    return json.loads(CUBE_PATH.read_text())


def test_population_cube_reconciles_complete_governed_population() -> None:
    cube = load_cube()
    population = cube["population"]
    assert population == {
        "collision_free_records": 4_645_719,
        "matched_records": 2_065_537,
        "pending_records": 457_327,
        "statistical_records": 5_008_334,
    }
    national = next(
        row
        for row in cube["portfolio_slices"]
        if row["district_code"] is None and row["nature_family"] is None
    )
    assert national["total_records"] == population["statistical_records"]
    assert national["pending_records"] == population["pending_records"]
    assert national["pending_records"] + national["terminated_records"] == national["total_records"]


def test_population_cube_dimensions_and_national_series_reconcile() -> None:
    cube = load_cube()
    dimensions = cube["dimensions"]
    assert len(dimensions["districts"]) == 94
    assert len(dimensions["nature_families"]) == 14
    assert dimensions["filing_years"] == list(range(2010, 2027))

    national_filings = [
        row
        for row in cube["filing_series"]
        if row["district_code"] is None and row["nature_family"] is None
    ]
    national_pending_age = [
        row
        for row in cube["pending_age_series"]
        if row["district_code"] is None and row["nature_family"] is None
    ]
    assert sum(row["cohort_records"] for row in national_filings) == 5_008_334
    assert sum(row["pending_records"] for row in national_pending_age) == 457_327


def test_population_cube_is_identifier_free_thresholded_and_canonical() -> None:
    cube = load_cube()
    policy = cube["publication_policy"]
    minimum_support = policy["minimum_support"]
    assert policy["full_population_used"] is True
    assert policy["matter_level_rows"] == 0
    assert minimum_support == 200

    assert all(row["total_records"] >= minimum_support for row in cube["portfolio_slices"])
    assert all(row["cohort_records"] >= minimum_support for row in cube["filing_series"])
    assert all(row["pending_records"] >= minimum_support for row in cube["pending_age_series"])

    forbidden_keys = {
        "case_identifier",
        "source_record_identifier",
        "docket_number",
        "filed_date",
        "party_name",
        "judge_name",
        "attorney_name",
        "document_text",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(cube))
    canonical = json.dumps(cube, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    assert CUBE_PATH.read_text() == canonical
