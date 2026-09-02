from __future__ import annotations

import base64
import hashlib
import hmac
import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


class PublicationContractError(ValueError):
    pass


@dataclass(frozen=True)
class FieldRule:
    source_name: str
    public_name: str
    type: str
    null_rule: str
    purpose: str
    linkability: str
    status: str


@dataclass(frozen=True)
class PublicationContract:
    contract_id: str
    dataset_version: str
    schema_version: str
    grain: str
    source_snapshot_cutoff: date
    expected_statistical_records: int
    expected_collision_records: int
    expected_pending_records: int
    fields: tuple[FieldRule, ...]
    prohibited_exact_fields: frozenset[str]
    prohibited_name_fragments: tuple[str, ...]
    prohibited_value_patterns: tuple[re.Pattern[str], ...]
    opaque_key_version: int
    opaque_key_minimum_secret_bytes: int
    opaque_key_digest_bytes: int
    default_query_rows: int
    maximum_query_rows: int
    maximum_csv_rows: int
    ordinary_queries_may_fetch_all_partitions: bool
    source_attribution: str
    source_terms_url: str
    courtlistener_attribution: str
    courtlistener_terms_url: str
    dataset_terms: str
    download_publication_gate: str
    manifest_version: int
    manifest_required_fields: frozenset[str]
    partition_required_fields: frozenset[str]
    partition_path_pattern: re.Pattern[str]
    manifest_null_policy: str
    manifest_date_policy: str

    @property
    def allowed_fields(self) -> tuple[str, ...]:
        return tuple(field.public_name for field in self.fields if field.status != "deny")

    @property
    def classification_coverage(self) -> float:
        complete = sum(
            bool(
                field.source_name
                and field.type
                and field.null_rule
                and field.purpose
                and field.linkability
                and field.status in {"allow", "allow_transformed", "deny"}
            )
            for field in self.fields
        )
        return complete / len(self.fields) if self.fields else 0.0


def load_publication_contract(
    path: Path = Path("config/public-row-mart-v1.toml"),
) -> PublicationContract:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise PublicationContractError("publication contract version must be 1")
    fields = tuple(FieldRule(**item) for item in document["field"])
    public_names = [field.public_name for field in fields if field.status != "deny"]
    source_names = [field.source_name for field in fields]
    if len(source_names) != len(set(source_names)) or len(public_names) != len(set(public_names)):
        raise PublicationContractError("publication field names must be unique")
    if any(not name for name in public_names):
        raise PublicationContractError("allowed fields require a public name")
    prohibited = document["prohibited"]
    opaque_key = document["opaque_key"]
    exports = document["exports"]
    attribution = document["attribution"]
    courtlistener_terms = document["courtlistener_terms"]
    download_terms = document["download_terms"]
    manifest = document["manifest"]
    contract = PublicationContract(
        contract_id=document["contract_id"],
        dataset_version=document["dataset_version"],
        schema_version=document["schema_version"],
        grain=document["grain"],
        source_snapshot_cutoff=date.fromisoformat(document["source_snapshot_cutoff"]),
        expected_statistical_records=document["expected_statistical_records"],
        expected_collision_records=document["expected_collision_records"],
        expected_pending_records=document["expected_pending_records"],
        fields=fields,
        prohibited_exact_fields=frozenset(prohibited["exact_fields"]),
        prohibited_name_fragments=tuple(prohibited["name_fragments"]),
        prohibited_value_patterns=tuple(
            re.compile(pattern) for pattern in prohibited["value_patterns"]
        ),
        opaque_key_version=opaque_key["version"],
        opaque_key_minimum_secret_bytes=opaque_key["minimum_secret_bytes"],
        opaque_key_digest_bytes=opaque_key["digest_bytes"],
        default_query_rows=exports["default_query_rows"],
        maximum_query_rows=exports["maximum_query_rows"],
        maximum_csv_rows=exports["maximum_csv_rows"],
        ordinary_queries_may_fetch_all_partitions=exports[
            "ordinary_queries_may_fetch_all_partitions"
        ],
        source_attribution=attribution["required_notice"],
        source_terms_url=attribution["terms_url"],
        courtlistener_attribution=courtlistener_terms["required_notice"],
        courtlistener_terms_url=courtlistener_terms["terms_url"],
        dataset_terms=download_terms["notice"],
        download_publication_gate=download_terms["publication_gate"],
        manifest_version=manifest["version"],
        manifest_required_fields=frozenset(manifest["required_fields"]),
        partition_required_fields=frozenset(manifest["partition_required_fields"]),
        partition_path_pattern=re.compile(manifest["partition_path_pattern"]),
        manifest_null_policy=manifest["null_policy"],
        manifest_date_policy=manifest["date_policy"],
    )
    if contract.classification_coverage != 1.0:
        raise PublicationContractError("every proposed field requires a complete classification")
    if set(contract.allowed_fields) & contract.prohibited_exact_fields:
        raise PublicationContractError("allowed fields overlap the prohibited-field policy")
    if (
        not (
            0
            < contract.default_query_rows
            <= contract.maximum_query_rows
            <= contract.maximum_csv_rows
        )
        or contract.ordinary_queries_may_fetch_all_partitions
    ):
        raise PublicationContractError("export bounds must be positive, ordered, and fail closed")
    if not all(
        (
            contract.source_attribution,
            contract.source_terms_url,
            contract.courtlistener_attribution,
            contract.courtlistener_terms_url,
            contract.dataset_terms,
            contract.download_publication_gate,
        )
    ):
        raise PublicationContractError("attribution and download terms are required")
    return contract


def release_record_key(
    source_record_identifier: str,
    dataset_version: str,
    secret: bytes,
    contract: PublicationContract,
) -> str:
    if not source_record_identifier:
        raise PublicationContractError("source record identifier is required")
    if dataset_version != contract.dataset_version:
        raise PublicationContractError("opaque key dataset version does not match contract")
    if len(secret) < contract.opaque_key_minimum_secret_bytes:
        raise PublicationContractError("opaque key secret is shorter than contract minimum")
    message = f"v{contract.opaque_key_version}\0{dataset_version}\0{source_record_identifier}"
    digest = hmac.new(secret, message.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest[: contract.opaque_key_digest_bytes]).decode().rstrip("=")


def prohibited_findings(
    columns: Iterable[str], values: Iterable[object], contract: PublicationContract
) -> tuple[str, ...]:
    findings: set[str] = set()
    for column in columns:
        normalized = column.lower()
        if normalized in contract.prohibited_exact_fields or any(
            fragment in normalized for fragment in contract.prohibited_name_fragments
        ):
            findings.add(f"field:{column}")
    for value in values:
        if isinstance(value, str) and any(
            pattern.search(value) for pattern in contract.prohibited_value_patterns
        ):
            findings.add("value:prohibited-pattern")
    return tuple(sorted(findings))


def validate_candidate_rows(
    rows: Iterable[Mapping[str, Any]],
    contract: PublicationContract,
    *,
    expected_collision_records: int | None = None,
) -> None:
    materialized = list(rows)
    if not materialized:
        raise PublicationContractError("candidate rows are empty")
    allowed = set(contract.allowed_fields)
    keys: set[str] = set()
    collision_records = 0
    for row in materialized:
        if set(row) != allowed:
            raise PublicationContractError("candidate row schema does not match allowlist")
        findings = prohibited_findings(row, row.values(), contract)
        if findings:
            raise PublicationContractError(f"candidate row contains prohibited content: {findings}")
        key = row["release_record_key"]
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{22}", key):
            raise PublicationContractError("release record key does not match opaque-key contract")
        if key in keys:
            raise PublicationContractError("release record keys are not unique")
        keys.add(key)
        if row["dataset_version"] != contract.dataset_version:
            raise PublicationContractError("row dataset version does not match contract")
        if row["source_snapshot_cutoff"] != contract.source_snapshot_cutoff:
            raise PublicationContractError("row source cutoff does not match contract")
        filed_month = row["filed_month"]
        terminated_month = row["terminated_month"]
        if not isinstance(filed_month, date) or filed_month.day != 1:
            raise PublicationContractError("filed month must use first-day encoding")
        pending = row["pending_status"]
        observed = row["event_observed"]
        if not isinstance(pending, bool) or not isinstance(observed, bool) or pending == observed:
            raise PublicationContractError("pending and event-observed semantics are inconsistent")
        if pending != (terminated_month is None):
            raise PublicationContractError(
                "termination null rule is inconsistent with pending status"
            )
        if terminated_month is not None and (
            not isinstance(terminated_month, date)
            or terminated_month.day != 1
            or terminated_month < filed_month
        ):
            raise PublicationContractError("terminated month violates date policy")
        duration = row["duration_days"]
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
            raise PublicationContractError("duration must be a nonnegative integer")
        mapping_status = row["nature_of_suit_mapping_status"]
        code = row["nature_of_suit_code"]
        if mapping_status not in {"supported", "unsupported"} or (
            (mapping_status == "supported") != (code is not None)
        ):
            raise PublicationContractError("nature-of-suit null semantics are inconsistent")
        identity = row["identity_quality_status"]
        source_count = row["source_record_count"]
        if identity not in {"canonical", "collision"} or isinstance(source_count, bool):
            raise PublicationContractError("identity quality fields are invalid")
        if (identity == "canonical" and source_count != 1) or (
            identity == "collision" and (not isinstance(source_count, int) or source_count < 2)
        ):
            raise PublicationContractError("identity status does not match source-record count")
        collision_records += identity == "collision"
    if expected_collision_records is not None and collision_records != expected_collision_records:
        raise PublicationContractError("collision records do not reconcile to expected count")


def validate_manifest(manifest: Mapping[str, Any], contract: PublicationContract) -> None:
    if set(manifest) != contract.manifest_required_fields:
        raise PublicationContractError("manifest fields do not match contract")
    if (
        manifest["manifest_version"] != contract.manifest_version
        or manifest["contract_id"] != contract.contract_id
        or manifest["dataset_version"] != contract.dataset_version
        or manifest["schema_version"] != contract.schema_version
        or manifest["source_snapshot_cutoff"] != contract.source_snapshot_cutoff.isoformat()
        or manifest["source_attribution"] != contract.source_attribution
        or manifest["source_terms_url"] != contract.source_terms_url
        or manifest["courtlistener_attribution"] != contract.courtlistener_attribution
        or manifest["courtlistener_terms_url"] != contract.courtlistener_terms_url
        or manifest["dataset_terms"] != contract.dataset_terms
        or manifest["null_policy"] != contract.manifest_null_policy
        or manifest["date_policy"] != contract.manifest_date_policy
        or manifest["opaque_key_version"] != contract.opaque_key_version
        or manifest["total_records"] != contract.expected_statistical_records
    ):
        raise PublicationContractError("manifest is incompatible with publication contract")
    if (
        not isinstance(manifest["metric_registry_version"], str)
        or not manifest["metric_registry_version"]
    ):
        raise PublicationContractError("manifest metric registry version is required")
    if not isinstance(manifest["minimum_app_version"], str) or not re.fullmatch(
        r"[0-9]+[.][0-9]+[.][0-9]+", manifest["minimum_app_version"]
    ):
        raise PublicationContractError("manifest minimum application version is invalid")
    partitions = manifest["partitions"]
    if not isinstance(partitions, list) or not partitions:
        raise PublicationContractError("manifest requires at least one partition")
    paths: set[str] = set()
    rows = 0
    for partition in partitions:
        if (
            not isinstance(partition, Mapping)
            or set(partition) != contract.partition_required_fields
        ):
            raise PublicationContractError("partition fields do not match manifest contract")
        path = partition["path"]
        if not isinstance(path, str) or not contract.partition_path_pattern.fullmatch(path):
            raise PublicationContractError("partition path is not allowlisted")
        if path in paths:
            raise PublicationContractError("partition paths must be unique")
        paths.add(path)
        if (
            partition["dataset_version"] != contract.dataset_version
            or partition["schema_version"] != contract.schema_version
            or not isinstance(partition["filing_year"], int)
            or f"filing_year={partition['filing_year']}" not in path
            or not isinstance(partition["row_count"], int)
            or partition["row_count"] <= 0
            or not isinstance(partition["byte_size"], int)
            or partition["byte_size"] <= 0
            or not isinstance(partition["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", partition["sha256"])
        ):
            raise PublicationContractError("partition is incompatible with publication contract")
        rows += partition["row_count"]
    if rows != manifest["total_records"]:
        raise PublicationContractError("manifest partition rows do not reconcile")
