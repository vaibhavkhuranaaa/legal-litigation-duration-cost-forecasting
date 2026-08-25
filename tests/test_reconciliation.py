from __future__ import annotations

import bz2
import csv
import json
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase

import polars as pl

from litigation_planner.reconciliation import (
    REQUIRED_RECAP_SOURCE_COLUMNS,
    ReconciliationError,
    aggregate_fjc_ao_population,
    evaluate_review_packet,
    export_blinded_review_packet,
    extract_recap_dockets,
    load_reconciliation_contract,
    normalize_recap_row,
    promote_reviewed_matches,
)
from litigation_planner.security import file_sha256


class ReconciliationTest(TestCase):
    def setUp(self) -> None:
        self.contract = load_reconciliation_contract(Path("config/reconciliation.toml"))

    def valid_row(self) -> dict[str, str]:
        return {
            "id": "10",
            "court_id": "ilnd",
            "date_filed": "2020-01-02",
            "date_terminated": "2021-03-04",
            "docket_number_core": "2000123",
            "nature_of_suit": "110 Insurance",
            "jurisdiction_type": "3",
            "idb_data_id": "20",
            "pacer_case_id": "30",
            "federal_dn_case_type": "cv",
            "federal_dn_office_code": "01",
            "blocked": "f",
        }

    def review_frame(
        self, labels: list[str], reviewers: list[str | None] | None = None
    ) -> pl.DataFrame:
        return pl.DataFrame(
            {
                "review_label": labels,
                "reviewer": reviewers or ["reviewer"] * len(labels),
                "reviewed_at_utc": ["2026-08-13T00:00:00+00:00"] * len(labels),
                "candidate_source_sha256": ["c" * 64] * len(labels),
                "contract_sha256": [file_sha256(Path("config/reconciliation.toml"))] * len(labels),
                "match_rule_id": [self.contract.match_rule_id] * len(labels),
            }
        )

    def test_contract_has_complete_unique_district_mapping(self) -> None:
        self.assertEqual(len(self.contract.districts), 94)
        self.assertEqual(len(self.contract.court_ids), 94)
        self.assertEqual(self.contract.review_sample_size, 800)

    def test_normalization_keeps_only_bounded_metadata(self) -> None:
        normalized, reason = normalize_recap_row(self.valid_row(), self.contract)
        self.assertIsNone(reason)
        self.assertEqual(
            normalized[1:5],
            ("ilnd", "1", "2000123", self.contract.population_start.replace(year=2020, day=2)),
        )
        blocked = self.valid_row() | {"blocked": "t"}
        self.assertEqual(normalize_recap_row(blocked, self.contract)[1], "blocked")
        malformed = self.valid_row() | {"docket_number_core": "20-123"}
        self.assertEqual(normalize_recap_row(malformed, self.contract)[1], "invalid_docket_core")
        invalid_office = self.valid_row() | {"federal_dn_office_code": "10"}
        self.assertEqual(normalize_recap_row(invalid_office, self.contract)[1], "invalid_office")

    def test_extracts_private_idempotent_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "dockets.csv.bz2"
            columns = sorted(REQUIRED_RECAP_SOURCE_COLUMNS)
            rows = [
                self.valid_row(),
                self.valid_row() | {"id": "11", "federal_dn_case_type": "cr"},
                self.valid_row() | {"id": "12", "court_id": "jpml"},
            ]
            with bz2.open(source, "wt", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "source_id": "courtlistener_recap_dockets",
                        "snapshot_cutoff": self.contract.recap_snapshot_cutoff.isoformat(),
                        "artifact": {
                            "bytes": source.stat().st_size,
                            "sha256": file_sha256(source),
                        },
                    }
                ),
                encoding="utf-8",
            )
            success = extract_recap_dockets(source, manifest, root / "output", batch_size=1)
            before = success.stat().st_mtime_ns
            run = json.loads(success.read_text(encoding="utf-8"))
            self.assertEqual((run["rows_seen"], run["rows"]), (3, 1))
            self.assertEqual(extract_recap_dockets(source, manifest, root / "output"), success)
            self.assertEqual(success.stat().st_mtime_ns, before)
            frame = pl.read_parquet(next(success.parent.rglob("*.parquet")))
            self.assertNotIn("case_name", frame.columns)
            self.assertEqual(frame.select("court_id", "office_code").row(0), ("ilnd", "1"))

    def test_rejects_public_output(self) -> None:
        with self.assertRaisesRegex(ReconciliationError, "outside public repository"):
            extract_recap_dockets(
                Path("missing.bz2"), Path("missing.json"), Path("data/reconciliation")
            )

    def test_rejects_same_size_source_with_wrong_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bz2"
            source.write_bytes(b"not-a-real-source")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "source_id": "courtlistener_recap_dockets",
                        "snapshot_cutoff": self.contract.recap_snapshot_cutoff.isoformat(),
                        "artifact": {"bytes": source.stat().st_size, "sha256": "0" * 64},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ReconciliationError, "SHA-256"):
                extract_recap_dockets(source, manifest, root / "output")

    def test_fjc_ao_population_uses_ao_dates_and_pending_stock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fjc.zip"
            header = b"DISTRICT\tFDATEUSE\tTDATEUSE\tSTATUSCD\n"
            body = (
                b"00\t04/01/2025\t03/31/2026\tL\n"
                b"00\t03/31/2010\t\tS\n"
                b"01\t03/31/2026\t04/01/2026\tL\n"
            )
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("cv88on.txt", header + body)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "source_id": "fjc_civil_cumulative",
                        "snapshot_cutoff": "2026-03-31",
                        "artifact": {
                            "bytes": source.stat().st_size,
                            "sha256": file_sha256(source),
                        },
                    }
                ),
                encoding="utf-8",
            )
            success = aggregate_fjc_ao_population(
                source, manifest, root / "private-output", Path("config/reconciliation.toml")
            )
            run = json.loads(success.read_text(encoding="utf-8"))
            self.assertEqual((run["filed"], run["terminated"], run["pending"]), (2, 1, 1))

    def test_review_gate_uses_exact_lower_confidence_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = root / "review.parquet"
            self.review_frame(["true_match"] * 800).write_parquet(review)
            result_path = evaluate_review_packet(
                review, root / "result", Path("config/reconciliation.toml")
            )
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "passed")
            self.assertGreaterEqual(result["exact_two_sided_lower_bound"], 0.995)
            self.review_frame(["true_match"] * 799 + ["false_match"]).write_parquet(review)
            failed = json.loads(
                evaluate_review_packet(
                    review, root / "failed", Path("config/reconciliation.toml")
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(failed["status"], "failed")

    def test_review_export_is_blinded_and_stratified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidates = root / "candidates.parquet"
            rows = []
            for index in range(800):
                rows.append(
                    {
                        "candidate_status": "review_eligible",
                        "case_identifier": f"case-{index}",
                        "recap_docket_id": f"recap-{index}",
                        "district_code": "00" if index % 2 else "01",
                        "court_id": "med" if index % 2 else "mad",
                        "office_code": "1",
                        "docket_number_core": f"{index:07d}",
                        "filed_date": self.contract.population_start.replace(
                            year=2010 + index % 16
                        ),
                        "fjc_terminated_date": None,
                        "recap_terminated_date": None,
                        "fjc_nature_of_suit": "110",
                        "recap_nature_of_suit": (
                            '=HYPERLINK("https://example.invalid","x")'
                            if index == 0
                            else "Insurance"
                        ),
                        "idb_data_id": None,
                        "pacer_case_id": None,
                    }
                )
            pl.DataFrame(rows).write_parquet(candidates)
            review_path = export_blinded_review_packet(
                candidates, root / "review", Path("config/reconciliation.toml")
            )
            review = pl.read_parquet(review_path)
            csv_review = pl.read_csv(review_path.with_name("blinded_review.csv"))
            self.assertEqual(review.height, 800)
            self.assertEqual(review.get_column("review_label").null_count(), 800)
            self.assertEqual(review.get_column("court_id").n_unique(), 2)
            self.assertGreater(review.get_column("filing_year_band").n_unique(), 1)
            self.assertTrue(
                csv_review.filter(pl.col("recap_nature_of_suit").str.starts_with("'=")).height
            )

    def test_review_gate_requires_complete_reviewer_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            review = root / "review.parquet"
            self.review_frame(["true_match"] * 800, [None] * 800).write_parquet(review)
            with self.assertRaisesRegex(ReconciliationError, "reviewer"):
                evaluate_review_packet(review, root / "result")

    def test_promotion_rejects_failed_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = root / "review-result.json"
            result.write_text(
                json.dumps(
                    {
                        "status": "failed",
                        "reviewed": 800,
                        "exact_two_sided_lower_bound": 0.99,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ReconciliationError, "does not pass"):
                promote_reviewed_matches(Path("missing.duckdb"), result, root / "promotion")

    def test_promotion_writes_unique_matches_and_coverage(self) -> None:
        import duckdb

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            warehouse = root / "warehouse.duckdb"
            connection = duckdb.connect(str(warehouse))
            connection.execute("create schema analytics")
            connection.execute(
                """
                create table analytics.fct_fjc_recap_match_candidates as
                select * from (values
                    ('case-1', 'record-1', 'recap-1', '01', 'mad', '1', '2000001',
                     date '2020-01-01', null, null, '110', 'Insurance', null, null,
                     1, 1, 'review_eligible', 'fjc', 'recap', 1),
                    ('case-2', 'record-2', 'recap-2', '02', 'nhd', '1', '2100002',
                     date '2021-01-01', date '2022-01-01', date '2022-01-01', '442',
                     'Civil Rights', null, null, 1, 1, 'review_eligible', 'fjc', 'recap', 1)
                ) as candidates(
                    case_identifier, source_record_identifier, recap_docket_id, district_code,
                    court_id, office_code, docket_number_core, filed_date, fjc_terminated_date,
                    recap_terminated_date, fjc_nature_of_suit, recap_nature_of_suit, idb_data_id,
                    pacer_case_id, recap_candidates_for_fjc, fjc_candidates_for_recap,
                    candidate_status, fjc_source_digest, recap_source_digest,
                    reconciliation_contract_version
                )
                """
            )
            connection.execute(
                """
                create table analytics.fct_federal_civil_statistical_records as
                select * from (values
                    ('record-1', '01', date '2020-01-01', 'contract'),
                    ('record-2', '02', date '2021-01-01', 'civil rights'),
                    ('record-3', '02', date '2022-01-01', 'civil rights')
                ) as records(source_record_identifier, district_code, filed_date, nature_of_suit_family)
                """
            )
            connection.execute(
                """
                create table analytics.fct_federal_civil_cases as
                select * from (values ('case-1'), ('case-2'), ('case-3'))
                as cases(case_identifier)
                """
            )
            connection.close()
            candidates = root / "candidates.parquet"
            candidates.write_bytes(b"bound candidate fixture")
            review = root / "review.parquet"
            self.review_frame(["true_match"] * 800).with_columns(
                pl.lit(file_sha256(candidates)).alias("candidate_source_sha256")
            ).write_parquet(review)
            result = evaluate_review_packet(
                review, root / "result", Path("config/reconciliation.toml")
            )
            success = promote_reviewed_matches(
                warehouse,
                result,
                root / "promotion",
                review_packet_path=review,
                candidates_path=candidates,
            )
            summary = json.loads(success.read_text(encoding="utf-8"))
            self.assertEqual(summary["promoted_matches"], 2)
            self.assertEqual(summary["unresolved_collisions"], 0)
            self.assertEqual(
                pl.read_parquet(success.parent / "fjc_recap_matches.parquet").height, 2
            )
