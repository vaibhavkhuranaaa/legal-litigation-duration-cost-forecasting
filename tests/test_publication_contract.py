from datetime import date
from pathlib import Path

import pytest

from litigation_planner.publication_contract import (
    PublicationContractError,
    load_publication_contract,
    prohibited_findings,
    release_record_key,
    validate_candidate_rows,
    validate_manifest,
)

CONTRACT_PATH = Path("config/public-row-mart-v1.toml")


def contract():
    return load_publication_contract(CONTRACT_PATH)


def candidate_rows() -> list[dict[str, object]]:
    policy = contract()
    secret = b"m15-fixture-key-is-not-a-release-secret"
    rows: list[dict[str, object]] = []
    for source_id, identity, count, pending, mapping in (
        ("fixture-1", "canonical", 1, False, "supported"),
        ("fixture-2", "collision", 2, True, "unsupported"),
        ("fixture-3", "collision", 2, False, "supported"),
    ):
        rows.append(
            {
                "release_record_key": release_record_key(
                    source_id, policy.dataset_version, secret, policy
                ),
                "circuit_code": "7",
                "district_code": "ilnd",
                "filed_month": date(2020, 1, 1),
                "terminated_month": None if pending else date(2021, 2, 1),
                "pending_status": pending,
                "event_observed": not pending,
                "duration_days": 410 if pending else 397,
                "nature_of_suit_code": None if mapping == "unsupported" else "440",
                "nature_of_suit_family": "civil_rights",
                "nature_of_suit_mapping_status": mapping,
                "jurisdiction_code": "3",
                "origin_code": "1",
                "procedural_cohort": "ordinary_original",
                "identity_quality_status": identity,
                "source_record_count": count,
                "recap_match_available": identity == "canonical",
                "source_snapshot_cutoff": policy.source_snapshot_cutoff,
                "dataset_version": policy.dataset_version,
            }
        )
    return rows


def test_every_proposed_field_is_classified_and_public_schema_is_narrow() -> None:
    policy = contract()
    assert policy.classification_coverage == 1.0
    assert len(policy.fields) == 21
    assert len(policy.allowed_fields) == 19
    assert set(policy.allowed_fields).isdisjoint(policy.prohibited_exact_fields)
    assert {"office_code", "filed_date", "terminated_date", "docket_number"}.issubset(
        policy.prohibited_exact_fields
    )


def test_opaque_keys_are_deterministic_release_scoped_and_privately_keyed() -> None:
    policy = contract()
    secret = bytes(range(32))
    first = release_record_key("private-source-row-9", policy.dataset_version, secret, policy)
    assert first == release_record_key(
        "private-source-row-9", policy.dataset_version, secret, policy
    )
    assert first != release_record_key(
        "private-source-row-9", policy.dataset_version, bytes(reversed(range(32))), policy
    )
    assert "private-source-row" not in first
    with pytest.raises(PublicationContractError, match="dataset version"):
        release_record_key("private-source-row-9", "later-release", secret, policy)
    with pytest.raises(PublicationContractError, match="shorter"):
        release_record_key("private-source-row-9", policy.dataset_version, b"short", policy)


def test_candidate_fixture_preserves_collision_date_and_null_semantics() -> None:
    validate_candidate_rows(candidate_rows(), contract(), expected_collision_records=2)
    broken = candidate_rows()
    broken[1]["identity_quality_status"] = "canonical"
    with pytest.raises(PublicationContractError, match="identity status"):
        validate_candidate_rows(broken, contract(), expected_collision_records=2)


def test_prohibited_fields_and_values_fail_closed() -> None:
    policy = contract()
    assert prohibited_findings(
        ["release_record_key", "docket_number"],
        ["safe", "client_secret=not-a-real-secret"],
        policy,
    ) == ("field:docket_number", "value:prohibited-pattern")
    broken = candidate_rows()
    broken[0]["private_path"] = "/Users/example/private.parquet"
    with pytest.raises(PublicationContractError, match="schema"):
        validate_candidate_rows(broken, policy)


def test_exports_attribution_and_download_terms_fail_closed() -> None:
    policy = contract()
    assert (policy.default_query_rows, policy.maximum_query_rows, policy.maximum_csv_rows) == (
        200,
        10_000,
        50_000,
    )
    assert policy.ordinary_queries_may_fetch_all_partitions is False
    assert "Federal Judicial Center" in policy.source_attribution
    assert "Free Law Project" in policy.courtlistener_attribution
    assert "consumer report" in policy.dataset_terms
    assert "M22" in policy.download_publication_gate


def test_manifest_contract_is_complete_and_version_compatible() -> None:
    policy = contract()
    manifest = {
        "manifest_version": 1,
        "contract_id": policy.contract_id,
        "dataset_version": policy.dataset_version,
        "schema_version": policy.schema_version,
        "source_snapshot_cutoff": policy.source_snapshot_cutoff.isoformat(),
        "source_attribution": policy.source_attribution,
        "source_terms_url": policy.source_terms_url,
        "courtlistener_attribution": policy.courtlistener_attribution,
        "courtlistener_terms_url": policy.courtlistener_terms_url,
        "dataset_terms": policy.dataset_terms,
        "null_policy": policy.manifest_null_policy,
        "date_policy": policy.manifest_date_policy,
        "opaque_key_version": 1,
        "metric_registry_version": "metrics.v1",
        "minimum_app_version": "2.0.0",
        "total_records": policy.expected_statistical_records,
        "partitions": [
            {
                "path": "filing_year=2020/part-00000.parquet",
                "filing_year": 2020,
                "row_count": policy.expected_statistical_records,
                "byte_size": 64000000,
                "sha256": "a" * 64,
                "dataset_version": policy.dataset_version,
                "schema_version": policy.schema_version,
            }
        ],
    }
    validate_manifest(manifest, policy)
    manifest["schema_version"] = "2.0.0"
    with pytest.raises(PublicationContractError, match="incompatible"):
        validate_manifest(manifest, policy)
