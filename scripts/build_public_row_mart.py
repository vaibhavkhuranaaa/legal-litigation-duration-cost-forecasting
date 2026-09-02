from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb

from litigation_planner.publication_contract import (
    PublicationContract,
    PublicationContractError,
    load_publication_contract,
    validate_manifest,
)

if __package__:
    from scripts.build_representative_partition import (
        DEFAULT_ROW_GROUP_SIZE,
        _inside,
        _sql_string,
        build_partition,
    )
    from scripts.export_full_population import MINIMUM_SUPPORT, build_cube
else:
    from build_representative_partition import (
        DEFAULT_ROW_GROUP_SIZE,
        _inside,
        _sql_string,
        build_partition,
    )
    from export_full_population import MINIMUM_SUPPORT, build_cube

YEARS = tuple(range(2010, 2027))
RELEASE_BYTE_CEILING = 262_144_000
DEFAULT_METRIC_REGISTRY_VERSION = "metrics.v1"
DEFAULT_MINIMUM_APP_VERSION = "2.0.0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(
    contract: PublicationContract,
    partitions: list[dict[str, object]],
    *,
    metric_registry_version: str,
    minimum_app_version: str,
) -> dict[str, object]:
    manifest = {
        "manifest_version": contract.manifest_version,
        "contract_id": contract.contract_id,
        "dataset_version": contract.dataset_version,
        "schema_version": contract.schema_version,
        "source_snapshot_cutoff": contract.source_snapshot_cutoff.isoformat(),
        "source_attribution": contract.source_attribution,
        "source_terms_url": contract.source_terms_url,
        "courtlistener_attribution": contract.courtlistener_attribution,
        "courtlistener_terms_url": contract.courtlistener_terms_url,
        "dataset_terms": contract.dataset_terms,
        "null_policy": contract.manifest_null_policy,
        "date_policy": contract.manifest_date_policy,
        "opaque_key_version": contract.opaque_key_version,
        "metric_registry_version": metric_registry_version,
        "minimum_app_version": minimum_app_version,
        "total_records": sum(int(partition["row_count"]) for partition in partitions),
        "partitions": partitions,
    }
    validate_manifest(manifest, contract)
    return manifest


def _write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _scan_literal(root: Path) -> str:
    files = [root / f"filing_year={year}" / "part-00000.parquet" for year in YEARS]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise PublicationContractError(f"candidate partition is missing: {missing[0]}")
    return "[" + ",".join(_sql_string(str(path)) for path in files) + "]"


def _install_cube_views(connection: duckdb.DuckDBPyConnection, scan: str) -> None:
    connection.execute("create schema analytics")
    connection.execute(
        f"create view row_mart as select * from read_parquet({scan}, hive_partitioning = false)"
    )
    connection.execute(
        """
        create view analytics.mart_portfolio_summary as
        select
            district_code,
            nature_of_suit_family as nature_family,
            count(*)::bigint as total_records,
            count_if(identity_quality_status = 'canonical')::bigint
                as collision_free_records,
            count_if(pending_status)::bigint as pending_records,
            count_if(event_observed)::bigint as terminated_records,
            count_if(recap_match_available)::bigint as matched_records,
            count_if(nature_of_suit_mapping_status = 'supported')::bigint
                as supported_nature_records
        from row_mart
        group by district_code, nature_of_suit_family
        """
    )
    connection.execute(
        """
        create view analytics.mart_duration_summary as
        select
            district_code,
            nature_of_suit_family as nature_family,
            jurisdiction_code,
            origin_code,
            procedural_cohort,
            count(*)::bigint as support_count,
            count_if(event_observed)::bigint as observed_terminations,
            count_if(pending_status)::bigint as censored_records,
            avg(case when event_observed then duration_days end)::double
                as average_observed_duration_days
        from row_mart
        group by
            district_code,
            nature_of_suit_family,
            jurisdiction_code,
            origin_code,
            procedural_cohort
        """
    )
    connection.execute(
        """
        create view analytics.mart_filing_cohorts as
        select
            extract(year from filed_month)::bigint as filing_year,
            district_code,
            nature_of_suit_family as nature_family,
            count(*)::bigint as cohort_records,
            count_if(event_observed)::bigint as observed_terminations,
            count_if(pending_status)::bigint as pending_records,
            count_if(recap_match_available)::bigint as matched_records,
            sum(duration_days)::bigint as followup_days
        from row_mart
        group by filing_year, district_code, nature_of_suit_family
        """
    )
    connection.execute(
        """
        create view analytics.mart_pending_inventory as
        with pending as (
            select
                *,
                case
                    when duration_days < 365 then 'under_1_year'
                    when duration_days < 730 then '1_to_2_years'
                    when duration_days < 1825 then '2_to_5_years'
                    else '5_years_or_more'
                end as age_band
            from row_mart
            where pending_status
        )
        select
            district_code,
            nature_of_suit_family as nature_family,
            age_band,
            count(*)::bigint as pending_records,
            count_if(recap_match_available)::bigint as matched_pending_records,
            avg(duration_days)::double as average_age_days
        from pending
        group by district_code, nature_of_suit_family, age_band
        """
    )
    connection.execute(
        """
        create view analytics.stg_reconciliation_districts as
        select distinct district_code, district_code as court_id, district_code as ao_label
        from row_mart
        """
    )


def _max_difference(expected: Any, actual: Any, path: str = "cube") -> float:
    if isinstance(expected, bool) or isinstance(actual, bool):
        if expected is not actual:
            raise PublicationContractError(f"aggregate cube mismatch at {path}")
        return 0.0
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(expected) - float(actual))
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected) != set(actual):
            raise PublicationContractError(f"aggregate cube keys differ at {path}")
        return max(
            (_max_difference(expected[key], actual[key], f"{path}.{key}") for key in expected),
            default=0.0,
        )
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            raise PublicationContractError(f"aggregate cube lengths differ at {path}")
        return max(
            (
                _max_difference(left, right, f"{path}[{index}]")
                for index, (left, right) in enumerate(zip(expected, actual, strict=True))
            ),
            default=0.0,
        )
    if expected != actual:
        raise PublicationContractError(f"aggregate cube mismatch at {path}")
    return 0.0


def _exact_cube_projection(cube: dict[str, object]) -> dict[str, object]:
    portfolio = []
    for source in cube["portfolio_slices"]:
        row = {
            key: value
            for key, value in source.items()
            if key
            not in {
                "average_observed_duration_days",
                "match_coverage",
                "pending_share",
            }
        }
        average = source["average_observed_duration_days"]
        row["observed_duration_days"] = (
            None if average is None else round(average * source["observed_terminations"])
        )
        portfolio.append(row)

    pending_age = []
    for source in cube["pending_age_series"]:
        row = {key: value for key, value in source.items() if key != "average_age_days"}
        row["age_days"] = round(source["average_age_days"] * source["pending_records"])
        pending_age.append(row)

    return {
        "population": cube["population"],
        "portfolio_slices": portfolio,
        "filing_series": cube["filing_series"],
        "pending_age_series": pending_age,
        "nature_families": cube["nature_families"],
        "filing_years": cube["filing_years"],
        "district_codes": cube["district_codes"],
    }


def _cube_reconciliation(
    connection: duckdb.DuckDBPyConnection, approved_cube_path: Path
) -> dict[str, object]:
    approved = json.loads(approved_cube_path.read_text(encoding="utf-8"))
    candidate = build_cube(connection, minimum_support=MINIMUM_SUPPORT)
    expected = {
        "population": approved["population"],
        "portfolio_slices": approved["portfolio_slices"],
        "filing_series": approved["filing_series"],
        "pending_age_series": approved["pending_age_series"],
        "nature_families": approved["dimensions"]["nature_families"],
        "filing_years": approved["dimensions"]["filing_years"],
        "district_codes": sorted(
            district["district_code"] for district in approved["dimensions"]["districts"]
        ),
    }
    actual = {
        "population": candidate["population"],
        "portfolio_slices": candidate["portfolio_slices"],
        "filing_series": candidate["filing_series"],
        "pending_age_series": candidate["pending_age_series"],
        "nature_families": candidate["dimensions"]["nature_families"],
        "filing_years": candidate["dimensions"]["filing_years"],
        "district_codes": sorted(
            district["district_code"] for district in candidate["dimensions"]["districts"]
        ),
    }
    display_float_difference = _max_difference(expected, actual)
    maximum_difference = _max_difference(
        _exact_cube_projection(expected), _exact_cube_projection(actual)
    )
    if maximum_difference != 0.0:
        raise PublicationContractError(
            f"aggregate cube maximum absolute difference is {maximum_difference}"
        )
    return {
        "maximum_absolute_difference": maximum_difference,
        "display_float_max_abs_difference": display_float_difference,
        "portfolio_slices": len(candidate["portfolio_slices"]),
        "filing_slices": len(candidate["filing_series"]),
        "pending_age_slices": len(candidate["pending_age_series"]),
    }


def validate_candidate(
    root: Path,
    manifest: dict[str, object],
    contract: PublicationContract,
    approved_cube_path: Path,
) -> dict[str, object]:
    validate_manifest(manifest, contract)
    declared_bytes = 0
    for partition in manifest["partitions"]:
        path = root / partition["path"]
        if path.stat().st_size != partition["byte_size"] or _sha256(path) != partition["sha256"]:
            raise PublicationContractError(f"partition integrity mismatch: {partition['path']}")
        declared_bytes += int(partition["byte_size"])

    connection = duckdb.connect()
    try:
        _install_cube_views(connection, _scan_literal(root))
        physical = connection.execute(
            """
            select
                count(*) as row_count,
                count(distinct release_record_key) as distinct_keys,
                count_if(release_record_key is null) as null_keys,
                count_if(not regexp_full_match(release_record_key, '[A-Za-z0-9_-]{22}'))
                    as invalid_keys,
                count_if(identity_quality_status = 'collision') as collision_records,
                count_if(pending_status) as pending_records
            from row_mart
            """
        ).fetchone()
        cube = _cube_reconciliation(connection, approved_cube_path)
    finally:
        connection.close()
    if physical is None:
        raise PublicationContractError("candidate validation query returned no row")
    expected = (
        contract.expected_statistical_records,
        contract.expected_statistical_records,
        0,
        0,
        contract.expected_collision_records,
        contract.expected_pending_records,
    )
    if physical != expected:
        raise PublicationContractError(
            f"full mart failed reconciliation: actual={physical}, expected={expected}"
        )
    total_bytes = declared_bytes + (root / "manifest.json").stat().st_size
    if total_bytes > RELEASE_BYTE_CEILING:
        raise PublicationContractError(
            f"candidate is {total_bytes} bytes, above {RELEASE_BYTE_CEILING}"
        )
    return {
        "row_count": physical[0],
        "distinct_release_record_keys": physical[1],
        "record_key_uniqueness": physical[1] / physical[0],
        "collision_records": physical[4],
        "pending_records": physical[5],
        "partition_bytes": declared_bytes,
        "manifest_bytes": (root / "manifest.json").stat().st_size,
        "total_bytes": total_bytes,
        "release_byte_ceiling": RELEASE_BYTE_CEILING,
        "aggregate_reconciliation": cube,
    }


def compare_candidates(first: Path, second: Path) -> dict[str, object]:
    first_files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
    second_files = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
    if first_files != second_files:
        raise PublicationContractError("replay candidate file sets differ")
    differences = [
        str(path) for path in first_files if _sha256(first / path) != _sha256(second / path)
    ]
    if differences:
        raise PublicationContractError(f"replay candidate bytes differ: {differences[0]}")
    return {"identical": 1, "files_compared": len(first_files), "differences": 0}


def build_mart(
    *,
    warehouse: Path,
    output: Path,
    secret_path: Path,
    contract_path: Path,
    approved_cube_path: Path,
    row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
    metric_registry_version: str = DEFAULT_METRIC_REGISTRY_VERSION,
    minimum_app_version: str = DEFAULT_MINIMUM_APP_VERSION,
    compare_to: Path | None = None,
) -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    if _inside(output, repository):
        raise PublicationContractError("row mart must be written outside tracked Git")
    if output.exists():
        raise PublicationContractError("refusing to overwrite an existing row mart")
    contract = load_publication_contract(contract_path)
    summaries = []
    partitions = []
    for year in YEARS:
        relative = Path(f"filing_year={year}") / "part-00000.parquet"
        summary = build_partition(
            warehouse=warehouse,
            output=output / relative,
            secret_path=secret_path,
            contract_path=contract_path,
            year=year,
            row_group_size=row_group_size,
        )
        summaries.append(summary)
        partitions.append(
            {
                "path": relative.as_posix(),
                "filing_year": year,
                "row_count": summary["row_count"],
                "byte_size": summary["byte_size"],
                "sha256": summary["sha256"],
                "dataset_version": contract.dataset_version,
                "schema_version": contract.schema_version,
            }
        )
    manifest = _manifest(
        contract,
        partitions,
        metric_registry_version=metric_registry_version,
        minimum_app_version=minimum_app_version,
    )
    _write_manifest(output / "manifest.json", manifest)
    validation = validate_candidate(output, manifest, contract, approved_cube_path)
    replay = compare_candidates(compare_to, output) if compare_to else None
    return {
        "status": "validated",
        "purpose": "private M16 full serving-mart candidate; not approved for publication",
        "contract_id": contract.contract_id,
        "dataset_version": contract.dataset_version,
        "schema_version": contract.schema_version,
        "row_group_size": row_group_size,
        "partitions": summaries,
        "validation": validation,
        "deterministic_replay": replay,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate the private M16 row mart.")
    parser.add_argument("--warehouse", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--key-file", required=True, type=Path)
    parser.add_argument("--approved-cube", required=True, type=Path)
    parser.add_argument("--contract", default=Path("config/public-row-mart-v1.toml"), type=Path)
    parser.add_argument("--row-group-size", default=DEFAULT_ROW_GROUP_SIZE, type=int)
    parser.add_argument("--compare-to", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = build_mart(
        warehouse=args.warehouse,
        output=args.output,
        secret_path=args.key_file,
        contract_path=args.contract,
        approved_cube_path=args.approved_cube,
        row_group_size=args.row_group_size,
        compare_to=args.compare_to,
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.summary:
        if _inside(args.summary, Path(__file__).resolve().parents[1]):
            raise PublicationContractError("row-mart summary must remain outside tracked Git")
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
