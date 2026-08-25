import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import polars as pl

from litigation_planner.raw_platform import (
    RawPlatformError,
    cloud_layout,
    convert_fjc,
    load_contract,
)


def fixture_source(
    root: Path, rows: list[str | bytes], header: list[str] | None = None
) -> tuple[Path, Path]:
    contract = load_contract(Path("config/raw_platform.toml"))
    source_root = root / "sources"
    key = Path("fjc/fixture.zip")
    archive_path = source_root / key
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    columns = header or list(contract.source_columns)
    with zipfile.ZipFile(archive_path, "w") as archive:
        payload = "\t".join(columns).encode() + b"\n"
        payload += b"\n".join(row.encode() if isinstance(row, str) else row for row in rows) + b"\n"
        archive.writestr("cv88on.txt", payload)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    manifest = {
        "source_id": contract.source_id,
        "snapshot_cutoff": contract.snapshot_cutoff.isoformat(),
        "artifact": {"storage_key": key.as_posix(), "sha256": digest},
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path, source_root


class RawPlatformTest(TestCase):
    def test_partition_quarantine_and_idempotency(self) -> None:
        contract = load_contract(Path("config/raw_platform.toml"))
        values = {column: "" for column in contract.source_columns}
        values.update(
            {
                "CIRCUIT": "1",
                "DISTRICT": "00",
                "DOCKET": "1",
                "FILEDATE": "01/02/2026",
                "STATUSCD": "L",
                "TAPEYEAR": "2026",
            }
        )
        valid = "\t".join(values[column] for column in contract.source_columns)
        values["FILEDATE"] = "04/01/2026"
        poisoned = "\t".join(values[column] for column in contract.source_columns)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, source_root = fixture_source(root, [valid, poisoned])
            run_path = convert_fjc(manifest, source_root, root / "output", batch_size=1)
            before = run_path.stat().st_mtime_ns
            run = json.loads(run_path.read_text())
            self.assertEqual((run["rows"], run["rejected_rows"]), (1, 1))
            self.assertEqual(convert_fjc(manifest, source_root, root / "output"), run_path)
            self.assertEqual(run_path.stat().st_mtime_ns, before)
            parquet = next(run_path.parent.glob("filing_year=2026/*.parquet"))
            self.assertEqual(pl.read_parquet(parquet).height, 1)
            self.assertTrue(next((root / "output/quarantine").rglob("*.parquet")).is_file())

    def test_schema_failure_quarantines_and_replay_succeeds(self) -> None:
        contract = load_contract(Path("config/raw_platform.toml"))
        values = {column: "" for column in contract.source_columns}
        values.update({"FILEDATE": "01/02/2026", "STATUSCD": "L", "TAPEYEAR": "2026"})
        row = "\t".join(values[column] for column in contract.source_columns)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, source_root = fixture_source(root, [row], list(contract.source_columns[:-1]))
            with self.assertRaisesRegex(RawPlatformError, "header"):
                convert_fjc(manifest, source_root, root / "output")
            self.assertTrue(next((root / "output/quarantine").rglob("failure.json")).is_file())
            manifest, source_root = fixture_source(root, [row])
            replay = convert_fjc(manifest, source_root, root / "output")
            self.assertEqual(json.loads(replay.read_text())["status"], "completed")

    def test_excludes_non_utf8_party_field_before_polars(self) -> None:
        contract = load_contract(Path("config/raw_platform.toml"))
        values = {column: b"" for column in contract.source_columns}
        values.update(
            {
                "FILEDATE": b"01/02/2026",
                "STATUSCD": b"L",
                "TAPEYEAR": b"2026",
                "PLT": b"party\x9bname",
            }
        )
        row = b"\t".join(values[column] for column in contract.source_columns)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, source_root = fixture_source(root, [row])
            run_path = convert_fjc(manifest, source_root, root / "output")
            parquet = next(run_path.parent.glob("filing_year=2026/*.parquet"))
            frame = pl.read_parquet(parquet)
            self.assertEqual(frame.height, 1)
            self.assertNotIn("PLT", frame.columns)

    def test_cloud_layout_is_deterministic(self) -> None:
        contract = load_contract(Path("config/raw_platform.toml"))
        run = {"source_digest": "a" * 64, "snapshot_cutoff": "2026-03-31"}
        first = cloud_layout(contract, run)
        self.assertEqual(first, cloud_layout(contract, run))
        self.assertEqual(first["gcs"]["precondition"], "if_generation_match=0")
        self.assertEqual(first["bigquery"]["load_job_id"], "fjc_raw_" + "a" * 20 + "_v3")
        self.assertEqual(first["bigquery"]["write_disposition"], "WRITE_EMPTY")

    def test_product_window_and_structural_rows_reconcile(self) -> None:
        contract = load_contract(Path("config/raw_platform.toml"))

        def row(**overrides: str) -> str:
            values = {column: "" for column in contract.source_columns}
            values.update({"STATUSCD": "L", "TAPEYEAR": "2026", **overrides})
            return "\t".join(values[column] for column in contract.source_columns)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, source_root = fixture_source(
                root,
                [
                    row(FILEDATE="12/31/2009"),
                    row(FILEDATE="01/01/2010", CIRCUIT="0", DISTRICT="3A", DOCKET="-8"),
                    row(FILEDATE="04/01/2026"),
                    row(FILEDATE="01/01/2020") + "\textra",
                ],
            )
            run_path = convert_fjc(manifest, source_root, root / "output", batch_size=2)
            run = json.loads(run_path.read_text())
            self.assertEqual(
                (run["rows_seen"], run["rows"], run["excluded_rows"], run["rejected_rows"]),
                (4, 1, 1, 2),
            )
            frame = pl.read_parquet(next(run_path.parent.rglob("*.parquet")))
            self.assertEqual(
                frame.select("CIRCUIT", "DISTRICT", "DOCKET").row(0), ("0", "3A", "-8")
            )

    def test_null_status_is_quarantined(self) -> None:
        contract = load_contract(Path("config/raw_platform.toml"))
        values = {column: "" for column in contract.source_columns}
        values.update({"FILEDATE": "01/01/2020", "TAPEYEAR": "2026"})
        row = "\t".join(values[column] for column in contract.source_columns)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, source_root = fixture_source(root, [row])
            run = json.loads(convert_fjc(manifest, source_root, root / "output").read_text())
            self.assertEqual((run["rows_seen"], run["rows"], run["rejected_rows"]), (1, 0, 1))

    def test_rejects_public_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, source_root = fixture_source(root, [])
            with self.assertRaisesRegex(RawPlatformError, "outside public repository"):
                convert_fjc(manifest, source_root, Path("data/raw-platform"))

    def test_archive_budget_failure_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, source_root = fixture_source(root, [])
            with (
                patch("litigation_planner.security.MAX_ARCHIVE_MEMBERS", 0),
                self.assertRaisesRegex(RawPlatformError, "member count"),
            ):
                convert_fjc(manifest, source_root, root / "output")
