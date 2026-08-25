import bz2
import json
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from litigation_planner.acquisition import (
    AcquisitionError,
    SourceSpec,
    _validate_source_url,
    acquire_source,
    download,
    load_registry,
    main,
)


class AcquisitionTest(TestCase):
    def test_registry_has_unique_bounded_sources(self) -> None:
        sources = load_registry(Path("config/sources.toml"))
        self.assertEqual(len(sources), 11)
        self.assertTrue(all(source.max_bytes > 0 for source in sources.values()))

    def test_validates_tabular_zip_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "cases.zip"
            with zipfile.ZipFile(artifact, "w") as archive:
                archive.writestr("cases.tsv", "COURT\tFILEDATE\n1\t2026-01-01\n")
            spec = SourceSpec(
                id="fixture",
                name="Fixture",
                url="https://example.invalid/cases.zip",
                filename="cases.zip",
                snapshot_cutoff="2026-03-31",
                kind="tabular_zip",
                max_bytes=10_000,
                terms_url="https://example.invalid/terms",
            )
            manifest_path = acquire_source(spec, root / "raw", root / "manifests", artifact)
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["validation"]["status"], "valid")
            self.assertEqual(
                manifest["validation"]["schema"]["summary"]["columns"],
                ["COURT", "FILEDATE"],
            )

    def test_validates_required_bzip2_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "dockets.csv.bz2"
            with bz2.open(artifact, "wt", encoding="utf-8", newline="") as output:
                output.write("id,court_id,date_filed\n1,txnd,2026-01-01\n")
            spec = SourceSpec(
                id="fixture",
                name="Fixture",
                url="https://example.invalid/dockets.csv.bz2",
                filename="dockets.csv.bz2",
                snapshot_cutoff="2026-06-30",
                kind="csv_bz2",
                max_bytes=10_000,
                terms_url="https://example.invalid/terms",
                required_columns=("id", "court_id", "date_filed"),
            )
            manifest_path = acquire_source(spec, root / "raw", root / "manifests", artifact)
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["validation"]["schema"]["summary"]["kind"], "csv")

    def test_download_retries_transient_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "artifact.pdf"
            spec = SourceSpec(
                id="fixture",
                name="Fixture",
                url="https://example.invalid/artifact.pdf",
                filename="artifact.pdf",
                snapshot_cutoff="2026-03-31",
                kind="pdf",
                max_bytes=10_000,
                terms_url="https://example.invalid/terms",
            )
            attempts = 0

            def fake_download(_spec: SourceSpec, partial: Path) -> dict[str, str]:
                nonlocal attempts
                attempts += 1
                if attempts < 3:
                    raise OSError("transient")
                partial.write_bytes(b"%PDF-1.7\n%%EOF\n")
                return {"etag": "fixture"}

            with (
                patch("litigation_planner.acquisition._download_once", side_effect=fake_download),
                patch("litigation_planner.acquisition.time.sleep"),
            ):
                self.assertEqual(download(spec, destination), {"etag": "fixture"})
            self.assertEqual(attempts, 3)
            self.assertTrue(destination.is_file())

    def test_cli_rejects_public_repository_storage(self) -> None:
        with self.assertRaisesRegex(AcquisitionError, "outside public repository"):
            main(
                [
                    "--source",
                    "fjc_civil_codebook",
                    "--data-root",
                    "data/raw",
                    "--manifest-dir",
                    "data/manifests",
                ]
            )

    def test_registry_rejects_traversal_components(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "sources.toml"
            registry.write_text(
                """
version = 1
[[source]]
id = "../escape"
name = "Unsafe"
url = "https://www.fjc.gov/source.zip"
filename = "source.zip"
snapshot_cutoff = "2026-03-31"
kind = "tabular_zip"
max_bytes = 1000
terms_url = "https://www.fjc.gov/terms"
""".strip()
            )
            with self.assertRaisesRegex(AcquisitionError, "boundary"):
                load_registry(registry)

    def test_source_url_rejects_internal_and_unapproved_hosts(self) -> None:
        for url in (
            "http://www.fjc.gov/source.zip",
            "https://127.0.0.1/source.zip",
            "https://example.invalid/source.zip",
        ):
            with self.subTest(url=url), self.assertRaisesRegex(AcquisitionError, "approved"):
                _validate_source_url(url)

    def test_archive_member_budget_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "cases.zip"
            with zipfile.ZipFile(artifact, "w") as archive:
                archive.writestr("cases.tsv", "COURT\tFILEDATE\n1\t2026-01-01\n")
                archive.writestr("extra.txt", "extra")
            spec = SourceSpec(
                id="fixture",
                name="Fixture",
                url="https://www.fjc.gov/cases.zip",
                filename="cases.zip",
                snapshot_cutoff="2026-03-31",
                kind="tabular_zip",
                max_bytes=10_000,
                terms_url="https://www.fjc.gov/terms",
            )
            with (
                patch("litigation_planner.security.MAX_ARCHIVE_MEMBERS", 1),
                self.assertRaisesRegex(AcquisitionError, "member count"),
            ):
                acquire_source(spec, root / "raw", root / "manifests", artifact)
