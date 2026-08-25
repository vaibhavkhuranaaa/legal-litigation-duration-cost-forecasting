from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import shutil
import sys
import tempfile
import time
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import polars as pl

from litigation_planner.acquisition import file_sha256
from litigation_planner.security import (
    MAX_LINE_BYTES,
    SecurityBoundaryError,
    validate_zip_budget,
)

YEAR_PATTERN = re.compile(r"^\d{4}$")
PRODUCT_START = date(2010, 1, 1)


class RawPlatformError(RuntimeError):
    pass


@dataclass(frozen=True)
class RawContract:
    source_id: str
    snapshot_cutoff: date
    partition_field: str
    contract_version: int
    source_columns: tuple[str, ...]
    columns: tuple[str, ...]
    gcs_prefix: str
    bigquery_table: str
    bigquery_partition_field: str
    bigquery_cluster_fields: tuple[str, ...]
    bigquery_write_disposition: str


def load_contract(path: Path) -> RawContract:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise RawPlatformError("raw platform contract version must be 1")
    source = document["fjc_civil"]
    bigquery = document["bigquery"]
    source_columns = tuple(source["source_columns"])
    columns = tuple(source["selected_columns"])
    if len(source_columns) != len(set(source_columns)) or len(columns) != len(set(columns)):
        raise RawPlatformError("raw columns must be unique")
    if missing := sorted(set(columns).difference(source_columns)):
        raise RawPlatformError(f"selected columns absent from source: {missing}")
    return RawContract(
        source_id=source["source_id"],
        snapshot_cutoff=date.fromisoformat(source["snapshot_cutoff"]),
        partition_field=source["partition_field"],
        contract_version=source["contract_version"],
        source_columns=source_columns,
        columns=columns,
        gcs_prefix=document["gcs"]["object_prefix"].strip("/"),
        bigquery_table=bigquery["table"],
        bigquery_partition_field=bigquery["partition_field"],
        bigquery_cluster_fields=tuple(bigquery["cluster_fields"]),
        bigquery_write_disposition=bigquery["write_disposition"],
    )


def require_private_output(path: Path) -> None:
    repository = Path(__file__).resolve().parents[2]
    try:
        path.resolve().relative_to(repository)
    except ValueError:
        return
    raise RawPlatformError("raw platform output must be outside public repository")


def _source_from_manifest(manifest_path: Path, source_root: Path) -> tuple[dict[str, object], Path]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    storage_key = manifest.get("artifact", {}).get("storage_key")
    if not isinstance(storage_key, str) or storage_key.startswith("retained:"):
        raise RawPlatformError("source manifest must reference private source-root storage")
    source = source_root / storage_key
    expected = manifest["artifact"]["sha256"]
    if not source.is_file() or file_sha256(source) != expected:
        raise RawPlatformError("source artifact does not match manifest")
    return manifest, source


def _extract_fjc(
    source: Path,
    directory: Path,
    quarantine: Path,
    source_columns: tuple[str, ...],
    selected_columns: tuple[str, ...],
) -> tuple[Path, int, int]:
    target = directory / "fjc.tsv"
    rejected_path = directory / "structural.ndjson"
    input_rows = rejected_rows = 0
    try:
        with zipfile.ZipFile(source) as archive:
            validate_zip_budget(source, archive)
            files = [item for item in archive.infolist() if not item.is_dir()]
            if len(files) != 1 or not files[0].filename.lower().endswith(".txt"):
                raise RawPlatformError("FJC archive must contain one text member")
            with (
                archive.open(files[0]) as source_file,
                target.open("wb") as output,
                rejected_path.open("w", encoding="utf-8") as rejected,
            ):
                header = tuple(
                    value.decode("ascii")
                    for value in source_file.readline().rstrip(b"\r\n").split(b"\t")
                )
                if header != source_columns:
                    raise RawPlatformError("FJC ordered header does not match raw contract")
                indexes = [header.index(column) for column in selected_columns]
                output.write(
                    b"source_row_number\t"
                    + b"\t".join(column.encode("ascii") for column in selected_columns)
                    + b"\n"
                )
                row_number = 0
                while line := source_file.readline(MAX_LINE_BYTES + 1):
                    if len(line) > MAX_LINE_BYTES:
                        raise RawPlatformError("FJC source line exceeds byte budget")
                    input_rows += 1
                    values = line.rstrip(b"\r\n").split(b"\t")
                    reason = None
                    if len(values) != len(source_columns):
                        reason = "field_count_mismatch"
                    else:
                        selected = [values[index] for index in indexes]
                        try:
                            for value in selected:
                                value.decode("utf-8")
                        except UnicodeDecodeError:
                            reason = "selected_field_invalid_utf8"
                    if reason:
                        rejected_rows += 1
                        rejected.write(
                            json.dumps(
                                {
                                    "source_row_number": row_number,
                                    "quarantine_reason": reason,
                                    "source_row_digest": hashlib.sha256(line).hexdigest(),
                                    "field_count": len(values),
                                },
                                sort_keys=True,
                            )
                            + "\n"
                        )
                    else:
                        output.write(
                            str(row_number).encode() + b"\t" + b"\t".join(selected) + b"\n"
                        )
                    row_number += 1
    except (OSError, SecurityBoundaryError, zipfile.BadZipFile) as error:
        raise RawPlatformError(f"cannot extract FJC archive: {error}") from error
    if rejected_rows:
        quarantine.mkdir(parents=True, exist_ok=True)
        pl.read_ndjson(rejected_path).write_parquet(
            quarantine / "structural.parquet", compression="zstd"
        )
    return target, input_rows, rejected_rows


def _write_batch(
    batch: pl.DataFrame,
    staging: Path,
    quarantine: Path,
    batch_index: int,
    contract: RawContract,
    source_digest: str,
) -> tuple[int, int, int, int]:
    metadata = [
        pl.lit(contract.snapshot_cutoff).cast(pl.Date).alias("source_snapshot_cutoff"),
        pl.lit(source_digest).alias("source_digest"),
        pl.lit(contract.contract_version).cast(pl.UInt16).alias("raw_contract_version"),
    ]
    batch = batch.with_columns(
        *metadata,
        pl.col("FILEDATE").str.to_date("%m/%d/%Y", strict=False).alias("filed_date_parsed"),
    )
    outside_window = pl.col("filed_date_parsed").is_not_null() & (
        pl.col("filed_date_parsed") < pl.lit(PRODUCT_START)
    )
    source_status_valid = (
        (pl.col("STATUSCD") == "L")
        | (
            (pl.col("STATUSCD") == "S")
            & (pl.col("TERMDATE") == "01/01/1900")
            & pl.col("TDATEUSE").is_null()
            & (pl.col("TAPEYEAR") == "2099")
        )
    ).fill_null(False)
    valid = (
        pl.col("filed_date_parsed").is_not_null()
        & (pl.col("filed_date_parsed") >= pl.lit(PRODUCT_START))
        & (pl.col("filed_date_parsed") <= pl.lit(contract.snapshot_cutoff))
        & source_status_valid
    )
    excluded = batch.filter(outside_window)
    rejected = batch.filter(~outside_window & ~valid).with_columns(
        pl.when(pl.col("filed_date_parsed").is_null())
        .then(pl.lit("invalid_filed_date"))
        .when(pl.col("filed_date_parsed") > pl.lit(contract.snapshot_cutoff))
        .then(pl.lit("filed_after_snapshot"))
        .otherwise(pl.lit("invalid_status_sentinel"))
        .alias("quarantine_reason")
    )
    accepted = batch.filter(valid).with_columns(
        pl.col("filed_date_parsed").dt.year().cast(pl.String).alias("filing_year")
    )
    if rejected.height:
        quarantine.mkdir(parents=True, exist_ok=True)
        rejected.select(
            "source_row_number", "quarantine_reason", "source_digest", "raw_contract_version"
        ).write_parquet(quarantine / f"row-contract-{batch_index:05d}.parquet", compression="zstd")
    partitions = 0
    for key, frame in accepted.partition_by(contract.partition_field, as_dict=True).items():
        year = key[0] if isinstance(key, tuple) else key
        if not isinstance(year, str) or not YEAR_PATTERN.fullmatch(year):
            raise RawPlatformError("invalid partition value escaped row contract")
        directory = staging / f"{contract.partition_field}={year}"
        directory.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(directory / f"part-{batch_index:05d}.parquet", compression="zstd")
        partitions += 1
    return accepted.height, excluded.height, rejected.height, partitions


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def cloud_layout(contract: RawContract, run_manifest: dict[str, object]) -> dict[str, object]:
    source_digest = str(run_manifest["source_digest"])
    snapshot = str(run_manifest["snapshot_cutoff"])
    return {
        "gcs": {
            "prefix": (
                f"{contract.gcs_prefix}/source_snapshot={snapshot}/"
                f"source_digest={source_digest[:16]}/contract_version={contract.contract_version}"
            ),
            "precondition": "if_generation_match=0",
        },
        "bigquery": {
            "table": contract.bigquery_table,
            "partition_field": contract.bigquery_partition_field,
            "cluster_fields": list(contract.bigquery_cluster_fields),
            "load_job_id": f"fjc_raw_{source_digest[:20]}_v{contract.contract_version}",
            "write_disposition": contract.bigquery_write_disposition,
        },
    }


def convert_fjc(
    manifest_path: Path,
    source_root: Path,
    output_root: Path,
    contract_path: Path = Path("config/raw_platform.toml"),
    batch_size: int = 250_000,
) -> Path:
    require_private_output(output_root)
    contract = load_contract(contract_path)
    source_manifest, source = _source_from_manifest(manifest_path, source_root)
    if source_manifest["source_id"] != contract.source_id:
        raise RawPlatformError("source ID does not match raw contract")
    source_digest = str(source_manifest["artifact"]["sha256"])
    snapshot = str(source_manifest["snapshot_cutoff"])
    if date.fromisoformat(snapshot) != contract.snapshot_cutoff:
        raise RawPlatformError("source cutoff does not match raw contract")
    final = (
        output_root
        / "fjc_civil"
        / f"source_snapshot={snapshot}"
        / f"source_digest={source_digest[:16]}"
        / f"contract_version={contract.contract_version}"
    )
    run_path = final / "_SUCCESS.json"
    if run_path.is_file():
        prior = json.loads(run_path.read_text(encoding="utf-8"))
        if prior.get("source_digest") != source_digest or prior.get("status") != "completed":
            raise RawPlatformError("existing raw run conflicts with source")
        return run_path

    output_root.mkdir(parents=True, exist_ok=True)
    staging = final.parent / f".{final.name}.staging-{uuid4().hex}"
    quarantine = (
        output_root
        / "quarantine"
        / "fjc_civil"
        / f"source_digest={source_digest[:16]}"
        / f"contract_version={contract.contract_version}"
    )
    started = time.perf_counter()
    rows = excluded_rows = rejected_rows = files = input_rows = 0
    try:
        with tempfile.TemporaryDirectory(dir=output_root, prefix="fjc-extract-") as directory:
            text_path, input_rows, structural_rejected = _extract_fjc(
                source,
                Path(directory),
                quarantine,
                contract.source_columns,
                contract.columns,
            )
            reader = pl.scan_csv(
                text_path,
                separator="\t",
                quote_char=None,
                schema={
                    "source_row_number": pl.UInt64,
                    **{column: pl.String for column in contract.columns},
                },
                truncate_ragged_lines=False,
            )
            for batch_index, batch in enumerate(reader.collect_batches(chunk_size=batch_size)):
                accepted, excluded, rejected, written = _write_batch(
                    batch,
                    staging,
                    quarantine,
                    batch_index,
                    contract,
                    source_digest,
                )
                rows += accepted
                excluded_rows += excluded
                rejected_rows += rejected
                files += written
            rejected_rows += structural_rejected
            if rows + excluded_rows + rejected_rows != input_rows:
                raise RawPlatformError(
                    "accepted, excluded, and quarantined rows do not reconcile to input"
                )
        elapsed = time.perf_counter() - started
        output_bytes = sum(path.stat().st_size for path in staging.rglob("*.parquet"))
        identity_payload = {
            "source_digest": source_digest,
            "contract_version": contract.contract_version,
            "columns": contract.columns,
            "partition_field": contract.partition_field,
        }
        dataset_id = hashlib.sha256(
            json.dumps(identity_payload, sort_keys=True).encode()
        ).hexdigest()
        run: dict[str, object] = {
            "version": 1,
            "status": "completed",
            "source_id": contract.source_id,
            "source_digest": source_digest,
            "snapshot_cutoff": snapshot,
            "raw_contract_version": contract.contract_version,
            "source_columns": len(contract.source_columns),
            "selected_columns": len(contract.columns),
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "rows": rows,
            "rows_seen": input_rows,
            "excluded_rows": excluded_rows,
            "rejected_rows": rejected_rows,
            "parquet_files": files,
            "input_bytes": source.stat().st_size,
            "output_bytes": output_bytes,
            "elapsed_seconds": round(elapsed, 6),
            "rows_per_second": round(rows / elapsed, 3),
            "compressed_mib_per_second": round(source.stat().st_size / 1024**2 / elapsed, 3),
            "peak_rss_bytes": _peak_rss_bytes(),
            "freshness_days": (datetime.now(UTC).date() - contract.snapshot_cutoff).days,
            "incremental_cost_usd": 0.0,
            "cost_per_million_rows_usd": 0.0,
            "dataset_id": dataset_id,
        }
        run["cloud_layout"] = cloud_layout(contract, run)
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "_SUCCESS.json").write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, final)
        return run_path
    except Exception as error:
        shutil.rmtree(staging, ignore_errors=True)
        quarantine.mkdir(parents=True, exist_ok=True)
        failure = {
            "version": 1,
            "status": "quarantined",
            "source_id": contract.source_id,
            "source_digest": source_digest,
            "failed_at_utc": datetime.now(UTC).isoformat(),
            "error_type": type(error).__name__,
            "error": str(error),
            "rows_seen": input_rows,
            "rows": rows,
            "excluded_rows": excluded_rows,
            "rejected_rows": rejected_rows,
        }
        failure_path = quarantine / "failure.json"
        failure_path.write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise RawPlatformError(str(error)) from error


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert FJC raw source into partitioned Parquet.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path("config/raw_platform.toml"))
    parser.add_argument("--batch-size", type=int, default=250_000)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run = convert_fjc(
        args.manifest,
        args.source_root,
        args.output_root,
        args.contract,
        args.batch_size,
    )
    print(run)
    return 0
