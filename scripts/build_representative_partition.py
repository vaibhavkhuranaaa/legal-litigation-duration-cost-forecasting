from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from litigation_planner.publication_contract import (
    PublicationContract,
    PublicationContractError,
    load_publication_contract,
    prohibited_findings,
    release_record_key,
)

DEFAULT_YEAR = 2019
DEFAULT_ROW_GROUP_SIZE = 65_536
SOURCE_TABLE = "analytics.fct_federal_civil_statistical_records"
MATCH_TABLE = "analytics.stg_promoted_fjc_recap_matches"


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _select_sql(dataset_version: str, year: int) -> str:
    return f"""
        select
            m17_release_record_key(records.source_record_identifier) as release_record_key,
            cast(records.circuit_code as varchar) as circuit_code,
            cast(records.district_code as varchar) as district_code,
            cast(date_trunc('month', records.filed_date) as date) as filed_month,
            cast(date_trunc('month', records.terminated_date) as date) as terminated_month,
            not records.event_observed as pending_status,
            records.event_observed,
            cast(records.duration_days as integer) as duration_days,
            cast(records.nature_of_suit_code as varchar) as nature_of_suit_code,
            cast(coalesce(records.nature_of_suit_family, 'unsupported') as varchar)
                as nature_of_suit_family,
            cast(records.nature_of_suit_mapping_status as varchar)
                as nature_of_suit_mapping_status,
            cast(records.jurisdiction_code as varchar) as jurisdiction_code,
            cast(records.origin_code as varchar) as origin_code,
            cast(
                case
                    when records.origin_code in ('6', '13') then 'multidistrict_litigation'
                    when coalesce(records.nature_of_suit_family, 'unsupported') = 'social_security'
                        then 'social_security_review'
                    when records.origin_code = '1' then 'ordinary_original'
                    else 'other_procedural_origin'
                end
                as varchar
            ) as procedural_cohort,
            cast(records.identity_quality_status as varchar) as identity_quality_status,
            cast(records.source_record_count as integer) as source_record_count,
            matches.source_record_identifier is not null as recap_match_available,
            records.source_snapshot_cutoff,
            cast({_sql_string(dataset_version)} as varchar) as dataset_version
        from {SOURCE_TABLE} as records
        left join (
            select distinct source_record_identifier
            from {MATCH_TABLE}
        ) as matches using (source_record_identifier)
        where extract(year from records.filed_date) = {year}
        order by district_code, nature_of_suit_family, release_record_key
    """


def _register_key_function(
    connection: duckdb.DuckDBPyConnection, secret: bytes, contract: PublicationContract
) -> None:
    connection.create_function(
        "m17_release_record_key",
        lambda source_id: release_record_key(source_id, contract.dataset_version, secret, contract),
        [duckdb.sqltypes.VARCHAR],
        duckdb.sqltypes.VARCHAR,
    )


def _validate_partition(
    connection: duckdb.DuckDBPyConnection,
    output: Path,
    year: int,
    contract: PublicationContract,
) -> dict[str, object]:
    source = connection.execute(
        f"""
        select
            count(*) as row_count,
            count_if(identity_quality_status = 'collision') as collision_count,
            count_if(not event_observed) as pending_count
        from {SOURCE_TABLE}
        where extract(year from filed_date) = ?
        """,
        [year],
    ).fetchone()
    if source is None:
        raise PublicationContractError("source reconciliation query returned no row")

    parquet_path = str(output)
    columns = tuple(
        row[0]
        for row in connection.execute(
            "describe select * from read_parquet(?, hive_partitioning = false)",
            [parquet_path],
        ).fetchall()
    )
    if columns != contract.allowed_fields:
        raise PublicationContractError("representative partition schema does not match allowlist")
    findings = prohibited_findings(columns, (), contract)
    if findings:
        raise PublicationContractError(
            f"representative partition has prohibited fields: {findings}"
        )

    actual = connection.execute(
        """
        select
            count(*) as row_count,
            count(distinct release_record_key) as distinct_keys,
            count_if(not regexp_full_match(release_record_key, '[A-Za-z0-9_-]{22}')) as bad_keys,
            count_if(identity_quality_status = 'collision') as collision_count,
            count_if(pending_status) as pending_count,
            count_if(pending_status = event_observed) as bad_status,
            count_if((terminated_month is null) <> pending_status) as bad_termination,
            count_if(filed_month <> date_trunc('month', filed_month)) as bad_filed_month,
            count_if(terminated_month is not null and terminated_month < filed_month)
                as bad_termination_order,
            count_if(duration_days < 0) as bad_duration,
            count_if(
                (nature_of_suit_mapping_status = 'supported')
                <> (nature_of_suit_code is not null)
            ) as bad_mapping,
            count_if(
                (identity_quality_status = 'canonical' and source_record_count <> 1)
                or (identity_quality_status = 'collision' and source_record_count < 2)
            ) as bad_identity,
            count_if(dataset_version <> ?) as bad_version,
            count_if(source_snapshot_cutoff <> ?) as bad_cutoff
        from read_parquet(?, hive_partitioning = false)
        """,
        [contract.dataset_version, contract.source_snapshot_cutoff, parquet_path],
    ).fetchone()
    if actual is None:
        raise PublicationContractError("partition validation query returned no row")

    expected = (source[0], source[0], 0, source[1], source[2], 0, 0, 0, 0, 0, 0, 0, 0, 0)
    if actual != expected:
        raise PublicationContractError(
            f"representative partition failed reconciliation: actual={actual}, expected={expected}"
        )

    text_columns = [
        name
        for name in contract.allowed_fields
        if name not in {"filed_month", "terminated_month", "source_snapshot_cutoff"}
    ]
    concatenated = ", ".join(f'cast("{name}" as varchar)' for name in text_columns)
    for pattern in contract.prohibited_value_patterns:
        count = connection.execute(
            f"select count(*) from read_parquet(?, hive_partitioning = false) "
            f"where regexp_matches(concat_ws(' ', {concatenated}), ?)",
            [parquet_path, pattern.pattern],
        ).fetchone()[0]
        if count:
            raise PublicationContractError(
                "representative partition contains prohibited value pattern"
            )

    row_groups = connection.execute(
        "select count(distinct row_group_id) from parquet_metadata(?)", [parquet_path]
    ).fetchone()[0]
    return {
        "row_count": actual[0],
        "distinct_release_record_keys": actual[1],
        "collision_records": actual[3],
        "pending_records": actual[4],
        "row_groups": row_groups,
        "prohibited_findings": 0,
    }


def build_partition(
    *,
    warehouse: Path,
    output: Path,
    secret_path: Path,
    contract_path: Path,
    year: int = DEFAULT_YEAR,
    row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
) -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    if _inside(output, repository):
        raise PublicationContractError("representative data must be written outside tracked Git")
    if _inside(secret_path, repository):
        raise PublicationContractError("private key file must remain outside tracked Git")
    if not warehouse.is_file() or not secret_path.is_file():
        raise PublicationContractError("warehouse and private key file are required")
    if output.exists():
        raise PublicationContractError("refusing to overwrite an existing representative partition")
    if not 2010 <= year <= 2026:
        raise PublicationContractError("representative filing year is outside the contract window")
    if row_group_size < 16_384 or row_group_size > 262_144:
        raise PublicationContractError("row group size must be between 16,384 and 262,144 rows")

    contract = load_publication_contract(contract_path)
    secret = secret_path.read_bytes()
    if len(secret) < contract.opaque_key_minimum_secret_bytes:
        raise PublicationContractError("private key file is shorter than the contract minimum")

    output.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(warehouse), read_only=True)
    try:
        _register_key_function(connection, secret, contract)
        query = _select_sql(contract.dataset_version, year)
        output_literal = _sql_string(str(output))
        connection.execute(
            f"copy ({query}) to {output_literal} "
            f"(format parquet, compression zstd, row_group_size {row_group_size})"
        )
        validation = _validate_partition(connection, output, year, contract)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "status": "validated",
        "purpose": "private annual public-row-mart partition; not a release manifest",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "contract_id": contract.contract_id,
        "dataset_version": contract.dataset_version,
        "schema_version": contract.schema_version,
        "filing_year": year,
        "row_group_size": row_group_size,
        "byte_size": output.stat().st_size,
        "sha256": digest,
        "path": str(output),
        **validation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build one private annual Parquet partition for the M17 browser benchmark."
    )
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path("config/public-row-mart-v1.toml"))
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--row-group-size", type=int, default=DEFAULT_ROW_GROUP_SIZE)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    result = build_partition(
        warehouse=args.warehouse,
        output=args.output,
        secret_path=args.key_file,
        contract_path=args.contract,
        year=args.year,
        row_group_size=args.row_group_size,
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.summary:
        if _inside(args.summary, Path(__file__).resolve().parents[1]):
            raise PublicationContractError("representative summary must remain outside tracked Git")
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
