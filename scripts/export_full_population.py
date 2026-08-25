"""Export a deterministic, matter-free analytical cube from governed marts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

MINIMUM_SUPPORT = 200
EXPECTED_STATISTICAL_RECORDS = 5_008_334
EXPECTED_PENDING_RECORDS = 457_327


def _records(
    connection: duckdb.DuckDBPyConnection, query: str, parameters: list[Any]
) -> list[dict[str, Any]]:
    cursor = connection.execute(query, parameters)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def build_cube(
    connection: duckdb.DuckDBPyConnection,
    *,
    minimum_support: int = MINIMUM_SUPPORT,
) -> dict[str, Any]:
    """Build the public aggregate contract from the complete private marts."""
    portfolio = _records(
        connection,
        """
        select
            district_code,
            nature_family,
            cast(sum(total_records) as bigint) as total_records,
            cast(sum(collision_free_records) as bigint) as collision_free_records,
            cast(sum(pending_records) as bigint) as pending_records,
            cast(sum(terminated_records) as bigint) as terminated_records,
            cast(sum(matched_records) as bigint) as matched_records,
            cast(sum(supported_nature_records) as bigint) as supported_nature_records
        from analytics.mart_portfolio_summary
        group by grouping sets ((district_code, nature_family), (district_code), (nature_family), ())
        having sum(total_records) >= ?
        order by district_code nulls first, nature_family nulls first
        """,
        [minimum_support],
    )

    durations = _records(
        connection,
        """
        select
            district_code,
            nature_family,
            cast(sum(support_count) as bigint) as duration_support_count,
            cast(sum(observed_terminations) as bigint) as observed_terminations,
            cast(sum(censored_records) as bigint) as censored_records,
            cast(
                sum(average_observed_duration_days * observed_terminations)
                / nullif(sum(observed_terminations), 0)
                as double
            ) as average_observed_duration_days
        from analytics.mart_duration_summary
        group by grouping sets ((district_code, nature_family), (district_code), (nature_family), ())
        having sum(support_count) >= ?
        """,
        [minimum_support],
    )
    duration_by_key = {(row["district_code"], row["nature_family"]): row for row in durations}
    for row in portfolio:
        row.update(
            duration_by_key.get(
                (row["district_code"], row["nature_family"]),
                {
                    "duration_support_count": None,
                    "observed_terminations": None,
                    "censored_records": None,
                    "average_observed_duration_days": None,
                },
            )
        )
        row["pending_share"] = row["pending_records"] / row["total_records"]
        row["match_coverage"] = row["matched_records"] / row["total_records"]

    filings = _records(
        connection,
        """
        select
            filing_year,
            district_code,
            nature_family,
            cast(sum(cohort_records) as bigint) as cohort_records,
            cast(sum(observed_terminations) as bigint) as observed_terminations,
            cast(sum(pending_records) as bigint) as pending_records,
            cast(sum(matched_records) as bigint) as matched_records,
            cast(sum(followup_days) as bigint) as followup_days
        from analytics.mart_filing_cohorts
        group by grouping sets (
            (filing_year, district_code, nature_family),
            (filing_year, district_code),
            (filing_year, nature_family),
            (filing_year)
        )
        having sum(cohort_records) >= ?
        order by filing_year, district_code nulls first, nature_family nulls first
        """,
        [minimum_support],
    )

    pending_age = _records(
        connection,
        """
        select
            age_band,
            district_code,
            nature_family,
            cast(sum(pending_records) as bigint) as pending_records,
            cast(sum(matched_pending_records) as bigint) as matched_pending_records,
            cast(
                sum(average_age_days * pending_records) / nullif(sum(pending_records), 0)
                as double
            ) as average_age_days
        from analytics.mart_pending_inventory
        group by grouping sets (
            (age_band, district_code, nature_family),
            (age_band, district_code),
            (age_band, nature_family),
            (age_band)
        )
        having sum(pending_records) >= ?
        order by
            case age_band
                when 'under_1_year' then 1
                when '1_to_2_years' then 2
                when '2_to_5_years' then 3
                else 4
            end,
            district_code nulls first,
            nature_family nulls first
        """,
        [minimum_support],
    )

    districts = _records(
        connection,
        """
        select distinct districts.district_code, districts.court_id, districts.ao_label
        from analytics.stg_reconciliation_districts as districts
        inner join analytics.mart_portfolio_summary as portfolio using (district_code)
        order by districts.court_id
        """,
        [],
    )
    nature_families = [
        row[0]
        for row in connection.execute(
            "select distinct nature_family from analytics.mart_portfolio_summary order by 1"
        ).fetchall()
    ]
    filing_years = [
        row[0]
        for row in connection.execute(
            "select distinct filing_year from analytics.mart_filing_cohorts order by 1"
        ).fetchall()
    ]

    national = next(
        row for row in portfolio if row["district_code"] is None and row["nature_family"] is None
    )
    if national["total_records"] != EXPECTED_STATISTICAL_RECORDS:
        raise ValueError(
            f"statistical population mismatch: {national['total_records']:,} != "
            f"{EXPECTED_STATISTICAL_RECORDS:,}"
        )
    if national["pending_records"] != EXPECTED_PENDING_RECORDS:
        raise ValueError(
            f"pending population mismatch: {national['pending_records']:,} != "
            f"{EXPECTED_PENDING_RECORDS:,}"
        )

    raw_counts = connection.execute(
        """
        select
            (select count(*) from analytics.mart_portfolio_summary),
            (select count(*) from analytics.mart_portfolio_summary where total_records >= ?),
            (select count(*) from analytics.mart_filing_cohorts),
            (select count(*) from analytics.mart_filing_cohorts where cohort_records >= ?),
            (select count(*) from analytics.mart_pending_inventory),
            (select count(*) from analytics.mart_pending_inventory where pending_records >= ?)
        """,
        [minimum_support, minimum_support, minimum_support],
    ).fetchone()
    if raw_counts is None:
        raise ValueError("aggregate mart counts are unavailable")

    return {
        "schema_version": "1",
        "source_snapshot": "2026-03-31",
        "population": {
            "statistical_records": national["total_records"],
            "pending_records": national["pending_records"],
            "collision_free_records": national["collision_free_records"],
            "matched_records": national["matched_records"],
        },
        "publication_policy": {
            "full_population_used": True,
            "matter_level_rows": 0,
            "minimum_support": minimum_support,
            "smallest_grain_cells": {
                "portfolio": {"available": raw_counts[0], "published": raw_counts[1]},
                "filing": {"available": raw_counts[2], "published": raw_counts[3]},
                "pending_age": {"available": raw_counts[4], "published": raw_counts[5]},
            },
            "limitation": (
                "Counts are observed public metadata. Small district-by-family cells are withheld; "
                "marginal and nationwide totals remain complete. Durations are descriptive, not forecasts."
            ),
        },
        "dimensions": {
            "districts": districts,
            "nature_families": nature_families,
            "filing_years": filing_years,
            "age_bands": [
                "under_1_year",
                "1_to_2_years",
                "2_to_5_years",
                "5_years_or_more",
            ],
        },
        "portfolio_slices": portfolio,
        "filing_series": filings,
        "pending_age_series": pending_age,
    }


def export_cube(warehouse: Path, output: Path, *, minimum_support: int = MINIMUM_SUPPORT) -> None:
    """Write the aggregate cube atomically with stable formatting."""
    connection = duckdb.connect(str(warehouse), read_only=True)
    try:
        cube = build_cube(connection, minimum_support=minimum_support)
    finally:
        connection.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    temporary.write_text(
        json.dumps(cube, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-support", default=MINIMUM_SUPPORT, type=int)
    args = parser.parse_args()
    export_cube(args.warehouse, args.output, minimum_support=args.minimum_support)
    print(args.output)


if __name__ == "__main__":
    main()
