from __future__ import annotations

import csv
import json
import os
import re
import shutil
import time
import tomllib
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

import polars as pl
from scipy.stats import beta

from litigation_planner.raw_platform import RawPlatformError, require_private_output
from litigation_planner.security import (
    MAX_LINE_BYTES,
    SecurityBoundaryError,
    bounded_bz2_text,
    file_sha256,
    read_limited,
    validate_zip_budget,
    verify_manifest_artifact,
)

DOCKET_CORE = re.compile(r"^\d{7}$")
XLSX_NAMESPACE = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAX_XLSX_XML_BYTES = 32 * 1024**2
RECAP_COLUMNS = (
    "recap_docket_id",
    "court_id",
    "office_code",
    "docket_number_core",
    "filed_date",
    "terminated_date",
    "nature_of_suit",
    "jurisdiction_type",
    "idb_data_id",
    "pacer_case_id",
    "source_row_number",
)
REQUIRED_RECAP_SOURCE_COLUMNS = {
    "id",
    "court_id",
    "date_filed",
    "date_terminated",
    "docket_number_core",
    "nature_of_suit",
    "jurisdiction_type",
    "idb_data_id",
    "pacer_case_id",
    "federal_dn_case_type",
    "federal_dn_office_code",
    "blocked",
}


class ReconciliationError(RuntimeError):
    pass


def _require_private_output(path: Path) -> None:
    try:
        require_private_output(path)
    except RawPlatformError as error:
        raise ReconciliationError(str(error)) from error


def _verified_source(source: Path, artifact: object) -> str:
    try:
        return verify_manifest_artifact(source, artifact)
    except SecurityBoundaryError as error:
        raise ReconciliationError(str(error)) from error


@dataclass(frozen=True)
class DistrictMapping:
    code: str
    court_id: str
    ao_label: str


@dataclass(frozen=True)
class ReconciliationContract:
    contract_version: int
    fjc_snapshot_cutoff: date
    recap_snapshot_cutoff: date
    population_start: date
    match_rule_id: str
    review_sample_size: int
    review_confidence: float
    precision_threshold: float
    ao_period_start: date
    ao_period_end: date
    ao_total_relative_difference_threshold: float
    districts: tuple[DistrictMapping, ...]
    court_ids: frozenset[str]


def load_reconciliation_contract(path: Path) -> ReconciliationContract:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ReconciliationError("reconciliation contract version must be 1")
    settings = document["reconciliation"]
    districts = tuple(DistrictMapping(**item) for item in document.get("district", []))
    for field in ("code", "court_id", "ao_label"):
        values = [getattr(item, field) for item in districts]
        if len(values) != 94 or len(values) != len(set(values)):
            raise ReconciliationError(f"district {field} mapping must contain 94 unique values")
    contract = ReconciliationContract(
        contract_version=settings["contract_version"],
        fjc_snapshot_cutoff=date.fromisoformat(settings["fjc_snapshot_cutoff"]),
        recap_snapshot_cutoff=date.fromisoformat(settings["recap_snapshot_cutoff"]),
        population_start=date.fromisoformat(settings["population_start"]),
        match_rule_id=settings["match_rule_id"],
        review_sample_size=settings["review_sample_size"],
        review_confidence=settings["review_confidence"],
        precision_threshold=settings["precision_threshold"],
        ao_period_start=date.fromisoformat(settings["ao_period_start"]),
        ao_period_end=date.fromisoformat(settings["ao_period_end"]),
        ao_total_relative_difference_threshold=settings["ao_total_relative_difference_threshold"],
        districts=districts,
        court_ids=frozenset(item.court_id for item in districts),
    )
    if not 0 < contract.precision_threshold <= 1 or not 0 < contract.review_confidence < 1:
        raise ReconciliationError("review thresholds must be probabilities")
    if contract.review_sample_size < 1 or contract.ao_period_end != contract.fjc_snapshot_cutoff:
        raise ReconciliationError("invalid review size or AO period cutoff")
    return contract


def normalize_office(value: str) -> str | None:
    stripped = value.strip()
    if not stripped.isdigit():
        return None
    normalized = str(int(stripped))
    return normalized if len(normalized) == 1 else None


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _normalize_recap_values(
    row: list[str], indexes: dict[str, int], contract: ReconciliationContract
) -> tuple[tuple[object, ...] | None, str | None]:
    if row[indexes["court_id"]] not in contract.court_ids:
        return None, "court_not_selected"
    if row[indexes["blocked"]].strip().lower() in {"1", "t", "true"}:
        return None, "blocked"
    if row[indexes["federal_dn_case_type"]].strip().lower() != "cv":
        return None, "not_civil"
    filed = _parse_date(row[indexes["date_filed"]])
    if filed is None or not contract.population_start <= filed <= contract.fjc_snapshot_cutoff:
        return None, "filed_outside_population"
    docket = row[indexes["docket_number_core"]].strip()
    if not DOCKET_CORE.fullmatch(docket):
        return None, "invalid_docket_core"
    office = normalize_office(row[indexes["federal_dn_office_code"]])
    if office is None:
        return None, "invalid_office"
    terminated = _parse_date(row[indexes["date_terminated"]])
    return (
        row[indexes["id"]].strip(),
        row[indexes["court_id"]],
        office,
        docket,
        filed,
        terminated,
        row[indexes["nature_of_suit"]].strip(),
        row[indexes["jurisdiction_type"]].strip(),
        row[indexes["idb_data_id"]].strip(),
        row[indexes["pacer_case_id"]].strip(),
    ), None


def normalize_recap_row(
    row: dict[str, str], contract: ReconciliationContract
) -> tuple[tuple[object, ...] | None, str | None]:
    columns = list(row)
    return _normalize_recap_values(
        [row[column] for column in columns], dict(zip(columns, range(len(columns)))), contract
    )


def _write_recap_batch(
    rows: list[tuple[object, ...]], staging: Path, batch_index: int, metadata: dict[str, object]
) -> int:
    frame = pl.DataFrame(
        rows,
        schema=[
            ("recap_docket_id", pl.String),
            ("court_id", pl.String),
            ("office_code", pl.String),
            ("docket_number_core", pl.String),
            ("filed_date", pl.Date),
            ("terminated_date", pl.Date),
            ("nature_of_suit", pl.String),
            ("jurisdiction_type", pl.String),
            ("idb_data_id", pl.String),
            ("pacer_case_id", pl.String),
            ("source_row_number", pl.UInt64),
        ],
        orient="row",
    ).with_columns(
        pl.lit(metadata["snapshot_cutoff"]).cast(pl.Date).alias("source_snapshot_cutoff"),
        pl.lit(metadata["source_digest"]).alias("source_digest"),
        pl.lit(metadata["contract_version"])
        .cast(pl.UInt16)
        .alias("reconciliation_contract_version"),
        pl.col("filed_date").dt.year().cast(pl.String).alias("filing_year"),
    )
    files = 0
    for key, partition in frame.partition_by("filing_year", as_dict=True).items():
        year = key[0] if isinstance(key, tuple) else key
        directory = staging / f"filing_year={year}"
        directory.mkdir(parents=True, exist_ok=True)
        partition.write_parquet(directory / f"part-{batch_index:05d}.parquet", compression="zstd")
        files += 1
    return files


def extract_recap_dockets(
    source: Path,
    manifest_path: Path,
    output_root: Path,
    contract_path: Path = Path("config/reconciliation.toml"),
    batch_size: int = 100_000,
) -> Path:
    _require_private_output(output_root)
    contract = load_reconciliation_contract(contract_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != "courtlistener_recap_dockets":
        raise ReconciliationError("CourtListener source manifest required")
    if date.fromisoformat(str(manifest["snapshot_cutoff"])) != contract.recap_snapshot_cutoff:
        raise ReconciliationError("CourtListener snapshot does not match contract")
    artifact = manifest["artifact"]
    digest = _verified_source(source, artifact)
    final = (
        output_root
        / "recap_dockets"
        / f"source_snapshot={contract.recap_snapshot_cutoff.isoformat()}"
        / f"source_digest={digest[:16]}"
        / f"contract_version={contract.contract_version}"
    )
    success = final / "_SUCCESS.json"
    if success.is_file():
        prior = json.loads(success.read_text(encoding="utf-8"))
        if prior.get("source_digest") != digest or prior.get("status") != "completed":
            raise ReconciliationError("existing RECAP extract conflicts with source")
        return success

    output_root.mkdir(parents=True, exist_ok=True)
    staging = final.parent / f".{final.name}.staging-{uuid4().hex}"
    quarantine = output_root / "quarantine" / "recap_dockets" / f"source_digest={digest[:16]}"
    started = time.perf_counter()
    seen = accepted = parquet_files = 0
    rejections: Counter[str] = Counter()
    batch: list[tuple[object, ...]] = []
    metadata = {
        "snapshot_cutoff": contract.recap_snapshot_cutoff,
        "source_digest": digest,
        "contract_version": contract.contract_version,
    }
    try:
        with bounded_bz2_text(source) as input_file:
            reader = csv.reader(input_file)
            header = next(reader, None)
            if header is None:
                raise ReconciliationError("CourtListener source has no header")
            if missing := sorted(REQUIRED_RECAP_SOURCE_COLUMNS.difference(header)):
                raise ReconciliationError(f"CourtListener source missing columns: {missing}")
            indexes = {column: position for position, column in enumerate(header)}
            for source_row_number, row in enumerate(reader, start=1):
                seen += 1
                if len(row) != len(header):
                    rejections["field_count_mismatch"] += 1
                    continue
                normalized, reason = _normalize_recap_values(row, indexes, contract)
                if normalized is None:
                    rejections[reason or "invalid"] += 1
                    continue
                batch.append((*normalized, source_row_number))
                accepted += 1
                if len(batch) == batch_size:
                    parquet_files += _write_recap_batch(batch, staging, parquet_files, metadata)
                    batch.clear()
            if batch:
                parquet_files += _write_recap_batch(batch, staging, parquet_files, metadata)
        elapsed = time.perf_counter() - started
        run = {
            "version": 1,
            "status": "completed",
            "source_id": "courtlistener_recap_dockets",
            "source_digest": digest,
            "snapshot_cutoff": contract.recap_snapshot_cutoff.isoformat(),
            "reconciliation_contract_version": contract.contract_version,
            "rows_seen": seen,
            "rows": accepted,
            "rejections": dict(sorted(rejections.items())),
            "parquet_files": parquet_files,
            "elapsed_seconds": round(elapsed, 6),
            "rows_per_second": round(seen / elapsed, 3),
            "incremental_cost_usd": 0.0,
            "completed_at_utc": datetime.now(UTC).isoformat(),
        }
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "_SUCCESS.json").write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, final)
        return success
    except Exception as error:
        shutil.rmtree(staging, ignore_errors=True)
        quarantine.mkdir(parents=True, exist_ok=True)
        (quarantine / "failure.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "status": "quarantined",
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "rows_seen": seen,
                    "rows": accepted,
                    "failed_at_utc": datetime.now(UTC).isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise ReconciliationError(str(error)) from error


def _xlsx_rows(path: Path) -> list[dict[int, str]]:
    try:
        with zipfile.ZipFile(path) as archive:
            validate_zip_budget(path, archive)
            shared: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                with archive.open("xl/sharedStrings.xml") as source:
                    root = ElementTree.fromstring(read_limited(source, MAX_XLSX_XML_BYTES))
                shared = [
                    "".join(node.text or "" for node in item.iterfind(".//main:t", XLSX_NAMESPACE))
                    for item in root.findall("main:si", XLSX_NAMESPACE)
                ]
            with archive.open("xl/worksheets/sheet1.xml") as source:
                sheet = ElementTree.fromstring(read_limited(source, MAX_XLSX_XML_BYTES))
    except (SecurityBoundaryError, zipfile.BadZipFile, ElementTree.ParseError) as error:
        raise ReconciliationError(f"invalid bounded XLSX: {error}") from error
    rows: list[dict[int, str]] = []
    for row in sheet.findall(".//main:sheetData/main:row", XLSX_NAMESPACE):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", XLSX_NAMESPACE):
            reference = cell.attrib.get("r", "")
            letters = "".join(character for character in reference if character.isalpha())
            column = 0
            for letter in letters:
                column = column * 26 + ord(letter.upper()) - 64
            value = cell.find("main:v", XLSX_NAMESPACE)
            raw = value.text if value is not None and value.text is not None else ""
            if cell.attrib.get("t") == "s" and raw:
                raw = shared[int(raw)]
            values[column - 1] = raw.strip()
        if values:
            rows.append(values)
    return rows


def prepare_reconciliation_references(
    ao_table_c: Path,
    manifest_path: Path,
    output_root: Path,
    contract_path: Path = Path("config/reconciliation.toml"),
) -> Path:
    _require_private_output(output_root)
    contract = load_reconciliation_contract(contract_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != "ao_civil_c":
        raise ReconciliationError("AO Table C source manifest required")
    if date.fromisoformat(str(manifest["snapshot_cutoff"])) != contract.ao_period_end:
        raise ReconciliationError("AO Table C snapshot does not match contract")
    digest = _verified_source(ao_table_c, manifest.get("artifact"))
    final = output_root / "references" / f"contract_version={contract.contract_version}"
    success = final / "_SUCCESS.json"
    if success.is_file():
        return success
    staging = final.parent / f".{final.name}.staging-{uuid4().hex}"
    rows = _xlsx_rows(ao_table_c)
    values_by_label = {row.get(0, "").replace("²", ""): row for row in rows}
    total = values_by_label.get("Total")
    if total is None:
        raise ReconciliationError("AO table C total row not found")
    ao_rows: list[dict[str, object]] = [
        {
            "district_code": "TOTAL",
            "ao_label": "Total",
            "filed": int(float(total[2])),
            "terminated": int(float(total[5])),
            "pending": int(float(total[8])),
        }
    ]
    for district in contract.districts:
        row = values_by_label.get(district.ao_label)
        if row is None:
            raise ReconciliationError(f"AO table C row not found: {district.ao_label}")
        ao_rows.append(
            {
                "district_code": district.code,
                "ao_label": district.ao_label,
                "filed": int(float(row[2])),
                "terminated": int(float(row[5])),
                "pending": int(float(row[8])),
            }
        )
    staging.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {"district_code": item.code, "court_id": item.court_id, "ao_label": item.ao_label}
            for item in contract.districts
        ]
    ).write_parquet(staging / "district_mapping.parquet", compression="zstd")
    pl.DataFrame(ao_rows).with_columns(
        pl.lit(contract.ao_period_start).cast(pl.Date).alias("period_start"),
        pl.lit(contract.ao_period_end).cast(pl.Date).alias("period_end"),
        pl.lit(contract.contract_version).cast(pl.UInt16).alias("reconciliation_contract_version"),
    ).write_parquet(staging / "ao_table_c.parquet", compression="zstd")
    run = {
        "version": 1,
        "status": "completed",
        "districts": len(contract.districts),
        "ao_rows": len(ao_rows),
        "ao_period_start": contract.ao_period_start.isoformat(),
        "ao_period_end": contract.ao_period_end.isoformat(),
        "source_digest": digest,
        "reconciliation_contract_version": contract.contract_version,
        "completed_at_utc": datetime.now(UTC).isoformat(),
    }
    (staging / "_SUCCESS.json").write_text(
        json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(staging, final)
    return success


def _ao_date_key(value: bytes) -> int | None:
    if len(value) != 10 or value[2:3] != b"/" or value[5:6] != b"/":
        return None
    try:
        return int(value[6:10] + value[0:2] + value[3:5])
    except ValueError:
        return None


def aggregate_fjc_ao_population(
    source: Path,
    manifest_path: Path,
    output_root: Path,
    contract_path: Path = Path("config/reconciliation.toml"),
) -> Path:
    """Aggregate the complete FJC snapshot to AO Table C's reporting grain."""
    _require_private_output(output_root)
    contract = load_reconciliation_contract(contract_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_id") != "fjc_civil_cumulative":
        raise ReconciliationError("FJC cumulative source manifest required")
    if date.fromisoformat(str(manifest["snapshot_cutoff"])) != contract.fjc_snapshot_cutoff:
        raise ReconciliationError("FJC snapshot does not match contract")
    artifact = manifest["artifact"]
    digest = _verified_source(source, artifact)
    final = output_root / "fjc_ao_population" / f"contract_version={contract.contract_version}"
    success = final / "_SUCCESS.json"
    if success.is_file():
        prior = json.loads(success.read_text(encoding="utf-8"))
        if prior.get("source_digest") != digest or prior.get("status") != "completed":
            raise ReconciliationError("existing FJC AO aggregate conflicts with source")
        return success

    staging = final.parent / f".{final.name}.staging-{uuid4().hex}"
    period_start = int(contract.ao_period_start.strftime("%Y%m%d"))
    period_end = int(contract.ao_period_end.strftime("%Y%m%d"))
    district_codes = {item.code for item in contract.districts}
    counts: Counter[tuple[str, str]] = Counter()
    rows_seen = structural_rejections = unknown_districts = 0
    started = time.perf_counter()
    try:
        with zipfile.ZipFile(source) as archive:
            validate_zip_budget(source, archive)
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) != 1 or not members[0].filename.lower().endswith(".txt"):
                raise ReconciliationError("FJC archive must contain one text member")
            with archive.open(members[0]) as input_file:
                header = tuple(
                    value.decode("ascii")
                    for value in input_file.readline().rstrip(b"\r\n").split(b"\t")
                )
                required = ("DISTRICT", "FDATEUSE", "TDATEUSE", "STATUSCD")
                if missing := sorted(set(required).difference(header)):
                    raise ReconciliationError(f"FJC source missing AO fields: {missing}")
                indexes = {column: header.index(column) for column in required}
                while line := input_file.readline(MAX_LINE_BYTES + 1):
                    if len(line) > MAX_LINE_BYTES:
                        raise ReconciliationError("FJC source line exceeds byte budget")
                    rows_seen += 1
                    values = line.rstrip(b"\r\n").split(b"\t")
                    if len(values) != len(header):
                        structural_rejections += 1
                        continue
                    district = values[indexes["DISTRICT"]].decode("ascii")
                    if district not in district_codes:
                        unknown_districts += 1
                        continue
                    filed_key = _ao_date_key(values[indexes["FDATEUSE"]])
                    terminated_key = _ao_date_key(values[indexes["TDATEUSE"]])
                    status = values[indexes["STATUSCD"]]
                    if filed_key is not None and period_start <= filed_key <= period_end:
                        counts[(district, "filed")] += 1
                        counts[("TOTAL", "filed")] += 1
                    if terminated_key is not None and period_start <= terminated_key <= period_end:
                        counts[(district, "terminated")] += 1
                        counts[("TOTAL", "terminated")] += 1
                    if status == b"S":
                        counts[(district, "pending")] += 1
                        counts[("TOTAL", "pending")] += 1
        aggregate_rows = []
        for district in ("TOTAL", *(item.code for item in contract.districts)):
            aggregate_rows.append(
                {
                    "district_code": district,
                    "filed": counts[(district, "filed")],
                    "terminated": counts[(district, "terminated")],
                    "pending": counts[(district, "pending")],
                }
            )
        staging.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(aggregate_rows).with_columns(
            pl.lit(contract.ao_period_start).cast(pl.Date).alias("period_start"),
            pl.lit(contract.ao_period_end).cast(pl.Date).alias("period_end"),
            pl.lit(contract.contract_version)
            .cast(pl.UInt16)
            .alias("reconciliation_contract_version"),
            pl.lit(digest).alias("source_digest"),
        ).write_parquet(staging / "fjc_ao_population.parquet", compression="zstd")
        elapsed = time.perf_counter() - started
        run = {
            "version": 1,
            "status": "completed",
            "source_id": "fjc_civil_cumulative",
            "source_digest": digest,
            "snapshot_cutoff": contract.fjc_snapshot_cutoff.isoformat(),
            "rows_seen": rows_seen,
            "structural_rejections": structural_rejections,
            "unknown_districts": unknown_districts,
            "aggregate_rows": len(aggregate_rows),
            "filed": counts[("TOTAL", "filed")],
            "terminated": counts[("TOTAL", "terminated")],
            "pending": counts[("TOTAL", "pending")],
            "elapsed_seconds": round(elapsed, 6),
            "incremental_cost_usd": 0.0,
            "completed_at_utc": datetime.now(UTC).isoformat(),
        }
        (staging / "_SUCCESS.json").write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, final)
        return success
    except Exception as error:
        shutil.rmtree(staging, ignore_errors=True)
        raise ReconciliationError(str(error)) from error


def export_blinded_review_packet(
    candidates_path: Path,
    output_root: Path,
    contract_path: Path = Path("config/reconciliation.toml"),
) -> Path:
    """Create a deterministic, private review sample without rule outcome columns."""
    _require_private_output(output_root)
    contract = load_reconciliation_contract(contract_path)
    candidate_source_sha256 = file_sha256(candidates_path)
    contract_sha256 = file_sha256(contract_path)
    candidates = pl.scan_parquet(candidates_path).filter(
        pl.col("candidate_status") == "review_eligible"
    )
    ranked = (
        candidates.with_columns(
            pl.when(pl.col("fjc_terminated_date").is_null())
            .then(pl.lit("pending"))
            .when(pl.col("recap_terminated_date").is_null())
            .then(pl.lit("missing_recap_termination"))
            .otherwise(pl.lit("terminated_agreement"))
            .alias("evidence_band"),
            (pl.col("filed_date").dt.year() // 5 * 5).alias("filing_year_band"),
            pl.concat_str(
                "court_id",
                "filed_date",
                "case_identifier",
                "recap_docket_id",
                separator="|",
            )
            .hash(seed=17)
            .alias("review_order"),
        )
        .sort("review_order")
        .collect()
    )
    priority = pl.concat(
        [
            ranked.group_by("court_id", maintain_order=True).head(1).select(ranked.columns),
            ranked.group_by("filing_year_band", maintain_order=True).head(1).select(ranked.columns),
            ranked.group_by("evidence_band", maintain_order=True).head(1).select(ranked.columns),
        ]
    ).unique(subset=["case_identifier", "recap_docket_id"], maintain_order=True)
    remainder = ranked.join(
        priority.select("case_identifier", "recap_docket_id"),
        on=["case_identifier", "recap_docket_id"],
        how="anti",
    )
    sample = pl.concat([priority, remainder]).head(contract.review_sample_size)
    if sample.height < contract.review_sample_size:
        raise ReconciliationError("not enough review-eligible candidates for the review sample")
    final = output_root / "review" / f"contract_version={contract.contract_version}"
    final.mkdir(parents=True, exist_ok=True)
    review = sample.select(
        pl.int_range(1, sample.height + 1, dtype=pl.UInt32).alias("review_item"),
        "case_identifier",
        "recap_docket_id",
        "district_code",
        "court_id",
        "office_code",
        "docket_number_core",
        "filed_date",
        "fjc_terminated_date",
        "recap_terminated_date",
        "fjc_nature_of_suit",
        "recap_nature_of_suit",
        "idb_data_id",
        "pacer_case_id",
        "filing_year_band",
        "evidence_band",
        pl.lit(candidate_source_sha256).alias("candidate_source_sha256"),
        pl.lit(contract_sha256).alias("contract_sha256"),
        pl.lit(contract.match_rule_id).alias("match_rule_id"),
        pl.lit(None, dtype=pl.String).alias("review_label"),
        pl.lit(None, dtype=pl.String).alias("reviewer"),
        pl.lit(None, dtype=pl.Datetime(time_zone="UTC")).alias("reviewed_at_utc"),
        pl.lit(None, dtype=pl.String).alias("review_notes"),
    )
    path = final / "blinded_review.parquet"
    review.write_parquet(path, compression="zstd")
    csv_review = review.with_columns(
        pl.when(pl.col(column).str.contains(r"^[=+\-@\t\r]"))
        .then(pl.lit("'") + pl.col(column))
        .otherwise(pl.col(column))
        .alias(column)
        for column, data_type in review.schema.items()
        if data_type == pl.String
    )
    csv_review.write_csv(final / "blinded_review.csv")
    return path


def evaluate_review_packet(
    review_path: Path,
    output_root: Path,
    contract_path: Path = Path("config/reconciliation.toml"),
) -> Path:
    """Evaluate completed human labels with a two-sided exact binomial lower bound."""
    _require_private_output(output_root)
    contract = load_reconciliation_contract(contract_path)
    review = (
        pl.read_csv(review_path, try_parse_dates=True)
        if review_path.suffix.lower() == ".csv"
        else pl.read_parquet(review_path)
    )
    required = {
        "review_label",
        "reviewer",
        "reviewed_at_utc",
        "candidate_source_sha256",
        "contract_sha256",
        "match_rule_id",
    }
    if not required.issubset(review.columns):
        raise ReconciliationError("review packet is missing required review metadata")
    if review.height != contract.review_sample_size:
        raise ReconciliationError(
            f"review packet must contain exactly {contract.review_sample_size} items"
        )
    bindings: dict[str, str] = {}
    for column in ("candidate_source_sha256", "contract_sha256", "match_rule_id"):
        values = review.get_column(column).drop_nulls().unique().to_list()
        if len(values) != 1 or not isinstance(values[0], str):
            raise ReconciliationError(f"review packet has inconsistent {column}")
        bindings[column] = values[0]
    if bindings["contract_sha256"] != file_sha256(contract_path):
        raise ReconciliationError("review packet contract binding does not match")
    if bindings["match_rule_id"] != contract.match_rule_id:
        raise ReconciliationError("review packet match rule does not match")
    labels = review.get_column("review_label")
    if labels.null_count() or set(labels.unique()) - {"true_match", "false_match"}:
        raise ReconciliationError("every review item needs a true_match or false_match label")
    if review.select(
        pl.any_horizontal(
            pl.col("reviewer").is_null()
            | (pl.col("reviewer").cast(pl.String).str.strip_chars() == ""),
            pl.col("reviewed_at_utc").is_null(),
        ).any()
    ).item():
        raise ReconciliationError("every review item needs reviewer and reviewed_at_utc metadata")
    reviewed = review.height
    true_matches = labels.eq("true_match").sum()
    false_matches = reviewed - true_matches
    alpha = 1 - contract.review_confidence
    lower_bound = (
        0.0 if true_matches == 0 else float(beta.ppf(alpha / 2, true_matches, false_matches + 1))
    )
    result = {
        "version": 1,
        "status": "passed" if lower_bound >= contract.precision_threshold else "failed",
        "reviewed": reviewed,
        "true_matches": true_matches,
        "false_matches": false_matches,
        "precision": true_matches / reviewed,
        "confidence": contract.review_confidence,
        "exact_two_sided_lower_bound": lower_bound,
        "threshold": contract.precision_threshold,
        "reviewers": sorted(review.get_column("reviewer").unique().to_list()),
        "review_packet_sha256": file_sha256(review_path),
        **bindings,
        "completed_at_utc": datetime.now(UTC).isoformat(),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "review_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def promote_reviewed_matches(
    warehouse: Path,
    review_result_path: Path,
    output_root: Path,
    contract_path: Path = Path("config/reconciliation.toml"),
    *,
    review_packet_path: Path | None = None,
    candidates_path: Path | None = None,
) -> Path:
    """Promote the reviewed exact-match rule and write collision and coverage evidence."""
    _require_private_output(output_root)
    contract = load_reconciliation_contract(contract_path)
    result = json.loads(review_result_path.read_text(encoding="utf-8"))
    if (
        result.get("status") != "passed"
        or result.get("reviewed") != contract.review_sample_size
        or result.get("exact_two_sided_lower_bound", 0) < contract.precision_threshold
    ):
        raise ReconciliationError("review result does not pass the reconciliation contract")
    if review_packet_path is None or candidates_path is None:
        raise ReconciliationError("promotion requires bound review packet and candidate source")
    if result.get("review_packet_sha256") != file_sha256(review_packet_path):
        raise ReconciliationError("review packet digest does not match review result")
    if result.get("candidate_source_sha256") != file_sha256(candidates_path):
        raise ReconciliationError("candidate source digest does not match review result")
    if result.get("contract_sha256") != file_sha256(contract_path):
        raise ReconciliationError("contract digest does not match review result")
    if result.get("match_rule_id") != contract.match_rule_id:
        raise ReconciliationError("match rule does not match review result")
    review = (
        pl.read_csv(review_packet_path, try_parse_dates=True)
        if review_packet_path.suffix.lower() == ".csv"
        else pl.read_parquet(review_packet_path)
    )
    labels = review.get_column("review_label")
    if review.height != contract.review_sample_size or labels.null_count():
        raise ReconciliationError("bound review packet is incomplete")
    true_matches = labels.eq("true_match").sum()
    false_matches = review.height - true_matches
    alpha = 1 - contract.review_confidence
    lower_bound = (
        0.0 if true_matches == 0 else float(beta.ppf(alpha / 2, true_matches, false_matches + 1))
    )
    if (
        true_matches != result.get("true_matches")
        or false_matches != result.get("false_matches")
        or abs(lower_bound - float(result["exact_two_sided_lower_bound"])) > 1e-12
    ):
        raise ReconciliationError("review statistics do not match bound packet")

    import duckdb

    connection = duckdb.connect(str(warehouse), read_only=True)
    try:
        audit = connection.execute(
            """
            select
                count(*) as promoted_matches,
                count(distinct case_identifier) as distinct_cases,
                count(distinct recap_docket_id) as distinct_recap_dockets,
                count(*) filter (
                    where recap_candidates_for_fjc != 1 or fjc_candidates_for_recap != 1
                ) as unresolved_collisions
            from analytics.fct_fjc_recap_match_candidates
            where candidate_status = 'review_eligible'
            """
        ).fetchone()
        if audit[0] != audit[1] or audit[0] != audit[2] or audit[3] != 0:
            raise ReconciliationError("review-eligible matches contain unresolved collisions")

        final = output_root / "promoted" / f"contract_version={contract.contract_version}"
        success = final / "_SUCCESS.json"
        if success.exists():
            return success
        staging = final.parent / f".{final.name}.staging-{uuid4().hex}"
        staging.mkdir(parents=True)
        promoted_path = staging / "fjc_recap_matches.parquet"
        coverage_path = staging / "match_coverage.parquet"
        reviewed_at = result["completed_at_utc"].replace("'", "''")
        rule_id = contract.match_rule_id.replace("'", "''")
        connection.execute(
            f"""
            copy (
                select
                    case_identifier,
                    source_record_identifier,
                    recap_docket_id,
                    district_code,
                    court_id,
                    office_code,
                    docket_number_core,
                    filed_date,
                    fjc_terminated_date,
                    recap_terminated_date,
                    fjc_nature_of_suit,
                    recap_nature_of_suit,
                    idb_data_id,
                    pacer_case_id,
                    fjc_source_digest,
                    recap_source_digest,
                    reconciliation_contract_version,
                    '{rule_id}' as match_rule_id,
                    timestamp '{reviewed_at}' as review_completed_at_utc
                from analytics.fct_fjc_recap_match_candidates
                where candidate_status = 'review_eligible'
            ) to '{promoted_path}' (format parquet, compression zstd)
            """
        )
        connection.execute(
            f"""
            copy (
                with promoted as (
                    select source_record_identifier
                    from analytics.fct_fjc_recap_match_candidates
                    where candidate_status = 'review_eligible'
                ), population as (
                    select
                        records.source_record_identifier,
                        records.district_code,
                        cast(year(records.filed_date) as varchar) as filing_year,
                        coalesce(records.nature_of_suit_family, 'unsupported') as nature_family,
                        promoted.source_record_identifier is not null as matched
                    from analytics.fct_federal_civil_statistical_records as records
                    left join promoted using (source_record_identifier)
                ), full_population as (
                    select 'full_statistical' as population_scope,
                           'overall' as dimension_type, 'all' as dimension_value,
                           count(*) as eligible_cases, count(*) filter (where matched) as promoted_matches
                    from population
                    union all
                    select 'full_statistical', 'district', district_code,
                           count(*), count(*) filter (where matched)
                    from population group by district_code
                    union all
                    select 'full_statistical', 'filing_year', filing_year,
                           count(*), count(*) filter (where matched)
                    from population group by filing_year
                    union all
                    select 'full_statistical', 'nature_family', nature_family,
                           count(*), count(*) filter (where matched)
                    from population group by nature_family
                ), collision_free as (
                    select 'collision_free' as population_scope,
                           'overall' as dimension_type, 'all' as dimension_value,
                           count(*) as eligible_cases,
                           count(*) filter (where candidates.case_identifier is not null) as promoted_matches
                    from analytics.fct_federal_civil_cases as cases
                    left join analytics.fct_fjc_recap_match_candidates as candidates
                        on cases.case_identifier = candidates.case_identifier
                        and candidates.candidate_status = 'review_eligible'
                )
                select *, promoted_matches::double / eligible_cases as coverage
                from (select * from full_population union all select * from collision_free)
                order by population_scope, dimension_type, dimension_value
            ) to '{coverage_path}' (format parquet, compression zstd)
            """
        )
        coverage = connection.execute(
            f"""
            select population_scope, eligible_cases, promoted_matches, coverage
            from read_parquet('{coverage_path}')
            where dimension_type = 'overall'
            order by population_scope
            """
        ).fetchall()
        summary = {
            "version": 1,
            "status": "completed",
            "match_rule_id": contract.match_rule_id,
            "promoted_matches": audit[0],
            "unresolved_collisions": audit[3],
            "review_result": result,
            "overall_coverage": [
                {
                    "population_scope": row[0],
                    "eligible_cases": row[1],
                    "promoted_matches": row[2],
                    "coverage": row[3],
                }
                for row in coverage
            ],
            "completed_at_utc": datetime.now(UTC).isoformat(),
        }
        (staging / "_SUCCESS.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, final)
        return success
    except Exception as error:
        if "staging" in locals():
            shutil.rmtree(staging, ignore_errors=True)
        if isinstance(error, ReconciliationError):
            raise
        raise ReconciliationError(str(error)) from error
    finally:
        connection.close()


def evaluate_ao_reconciliation(
    ao_path: Path,
    fjc_path: Path,
    output_root: Path,
    contract_path: Path = Path("config/reconciliation.toml"),
) -> Path:
    """Write a private cell-level AO comparison using predeclared tolerances."""
    _require_private_output(output_root)
    contract = load_reconciliation_contract(contract_path)
    keys = ["district_code", "measure"]
    ao = pl.read_parquet(ao_path).unpivot(
        on=["filed", "terminated", "pending"],
        index="district_code",
        variable_name="measure",
        value_name="ao_value",
    )
    fjc = pl.read_parquet(fjc_path).unpivot(
        on=["filed", "terminated", "pending"],
        index="district_code",
        variable_name="measure",
        value_name="fjc_value",
    )
    compared = (
        ao.join(fjc, on=keys, how="inner", validate="1:1")
        .with_columns(
            (pl.col("fjc_value") - pl.col("ao_value")).alias("difference"),
            ((pl.col("fjc_value") - pl.col("ao_value")).abs() / pl.col("ao_value"))
            .fill_nan(0.0)
            .alias("relative_difference"),
            pl.when(pl.col("district_code") == "TOTAL")
            .then(pl.lit(contract.ao_total_relative_difference_threshold))
            .otherwise(pl.lit(0.02))
            .alias("tolerance"),
        )
        .with_columns(
            (pl.col("relative_difference") <= pl.col("tolerance")).alias("passed"),
            (pl.col("district_code") == "TOTAL").alias("required_for_gate"),
        )
        .with_columns(
            pl.when(pl.col("difference") == 0)
            .then(pl.lit("exact"))
            .when(pl.col("district_code") == "TOTAL")
            .then(pl.lit("publication_version_lag"))
            .when(pl.col("passed"))
            .then(pl.lit("within_predeclared_district_tolerance"))
            .otherwise(pl.lit("district_definition_or_mdl_review_required"))
            .alias("reason_code"),
            pl.when(pl.col("passed"))
            .then(pl.lit("accepted"))
            .when(pl.col("required_for_gate"))
            .then(pl.lit("blocks_reconciliation"))
            .otherwise(pl.lit("retained_unresolved_district_diagnostic"))
            .alias("disposition"),
        )
        .sort(keys)
    )
    if compared.height != 285:
        raise ReconciliationError("AO comparison must contain 95 districts or totals by 3 measures")
    required = compared.filter(pl.col("required_for_gate"))
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "ao_table_c_reconciliation.parquet"
    compared.write_parquet(report_path, compression="zstd")
    summary = {
        "version": 1,
        "status": "passed" if required.get_column("passed").all() else "failed",
        "required_comparisons": required.height,
        "required_passed": required.get_column("passed").sum(),
        "required_pass_rate": required.get_column("passed").mean(),
        "total_relative_difference_threshold": contract.ao_total_relative_difference_threshold,
        "district_diagnostic_relative_difference_threshold": 0.02,
        "comparison_rows": compared.height,
        "completed_at_utc": datetime.now(UTC).isoformat(),
    }
    (output_root / "ao_table_c_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report_path


def export_candidate_mart(warehouse: Path, output_root: Path) -> Path:
    """Materialize the governed local candidate view as a private review input."""
    _require_private_output(output_root)
    import duckdb

    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "fjc_recap_match_candidates.parquet"
    staging = output_root / f".{path.name}.staging-{uuid4().hex}"
    connection = duckdb.connect(str(warehouse), read_only=True)
    try:
        connection.execute(
            "copy (select * from analytics.fct_fjc_recap_match_candidates) "
            f"to '{staging}' (format parquet, compression zstd)"
        )
    finally:
        connection.close()
    os.replace(staging, path)
    return path
