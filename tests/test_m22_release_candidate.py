import json
from pathlib import Path

import pytest

from litigation_planner.publication_contract import (
    PublicationContractError,
    load_publication_contract,
)
from scripts.build_public_row_mart import _manifest
from scripts.build_row_release_candidate import build_release_candidate, verify_release_candidate

PUBLIC_DATA_URL = "https://example.test/project/row-data/fjc-civil-2026-03-31.v1/"


def fixture_inputs(tmp_path: Path) -> dict[str, Path]:
    contract_path = Path("config/public-row-mart-v1.toml")
    contract = load_publication_contract(contract_path)
    app = tmp_path / "app"
    (app / "assets").mkdir(parents=True)
    (app / "index.html").write_text("<html></html>", encoding="utf-8")
    (app / "assets/app.js").write_text(
        f'const dataUrl="{PUBLIC_DATA_URL}"; const version="2.0.0";', encoding="utf-8"
    )
    row_mart = tmp_path / "row-mart"
    base = contract.expected_statistical_records // 17
    partitions = []
    for index, year in enumerate(range(2010, 2027)):
        relative = Path(f"filing_year={year}") / "part-00000.parquet"
        path = row_mart / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(f"PAR1-{year}".encode())
        count = base + (contract.expected_statistical_records - base * 17 if index == 16 else 0)
        partitions.append(
            {
                "path": relative.as_posix(),
                "filing_year": year,
                "row_count": count,
                "byte_size": path.stat().st_size,
                "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
                "dataset_version": contract.dataset_version,
                "schema_version": contract.schema_version,
            }
        )
    manifest = _manifest(
        contract,
        partitions,
        metric_registry_version="metrics.v1",
        minimum_app_version="2.0.0",
    )
    (row_mart / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    registry = tmp_path / "metrics.json"
    registry.write_text(
        json.dumps(
            {
                "registry_id": "metrics.v1",
                "dataset_version": contract.dataset_version,
                "schema_version": contract.schema_version,
            }
        ),
        encoding="utf-8",
    )
    package_json = tmp_path / "package.json"
    package_json.write_text('{"version":"2.0.0"}', encoding="utf-8")
    return {
        "app": app,
        "row_mart": row_mart,
        "semantic_registry": registry,
        "package_json": package_json,
        "contract_path": contract_path,
    }


def test_builds_and_verifies_deterministic_release_inventory(tmp_path: Path) -> None:
    inputs = fixture_inputs(tmp_path)
    output = tmp_path / "candidate"
    result = build_release_candidate(
        **inputs,
        approved_cube=None,
        public_data_url=PUBLIC_DATA_URL,
        output=output,
    )
    assert result["status"] == "local_candidate_validated"
    assert result["file_count"] == 23
    dictionary = json.loads(
        (output / "row-data/fjc-civil-2026-03-31.v1/data-dictionary.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(dictionary["fields"]) == 19
    assert {field["name"] for field in dictionary["fields"]} == set(
        load_publication_contract(Path("config/public-row-mart-v1.toml")).allowed_fields
    )
    assert verify_release_candidate(output) == {
        "file_count": result["file_count"],
        "total_bytes": result["total_bytes"],
        "digest": result["digest"],
    }
    (output / "assets/app.js").write_text("tampered", encoding="utf-8")
    with pytest.raises(PublicationContractError, match="do not match"):
        verify_release_candidate(output)


def test_refuses_incompatible_app_and_public_repository_output(tmp_path: Path) -> None:
    inputs = fixture_inputs(tmp_path)
    inputs["package_json"].write_text('{"version":"1.1.0"}', encoding="utf-8")
    with pytest.raises(PublicationContractError, match="application version"):
        build_release_candidate(
            **inputs,
            approved_cube=None,
            public_data_url=PUBLIC_DATA_URL,
            output=tmp_path / "bad-version",
        )
    inputs["package_json"].write_text('{"version":"2.0.0"}', encoding="utf-8")
    with pytest.raises(PublicationContractError, match="outside tracked Git"):
        build_release_candidate(
            **inputs,
            approved_cube=None,
            public_data_url=PUBLIC_DATA_URL,
            output=Path("data/m22-candidate"),
        )


def test_refuses_private_path_in_application_bundle(tmp_path: Path) -> None:
    inputs = fixture_inputs(tmp_path)
    (inputs["app"] / "assets/app.js").write_text(
        f'const dataUrl="{PUBLIC_DATA_URL}"; const version="2.0.0"; const path="/Users/me";',
        encoding="utf-8",
    )
    with pytest.raises(PublicationContractError, match="private filesystem path"):
        build_release_candidate(
            **inputs,
            approved_cube=None,
            public_data_url=PUBLIC_DATA_URL,
            output=tmp_path / "private-path",
        )
