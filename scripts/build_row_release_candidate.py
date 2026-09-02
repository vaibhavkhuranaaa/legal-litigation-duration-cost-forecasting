from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import duckdb

from litigation_planner.publication_contract import (
    PublicationContract,
    PublicationContractError,
    load_publication_contract,
    validate_manifest,
)
from scripts.build_public_row_mart import _scan_literal, _sha256, validate_candidate

RELEASE_VERSION = "2.0.0"
RELEASE_BYTE_CEILING = 262_144_000
TEXT_SUFFIXES = frozenset({".css", ".html", ".js", ".json", ".md", ".txt"})
CREDENTIAL_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{30,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "private filesystem path": re.compile(r"(?i)(/Users/|/home/|[A-Z]:\\Users\\)"),
}
ALLOWED_LIBRARY_LITERALS = ("/home/web_user",)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _files(root: Path) -> list[Path]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in root.rglob("*")):
        raise PublicationContractError("release candidate inputs must not contain symlinks")
    return files


def _inventory(root: Path, *, exclude: frozenset[str] = frozenset()) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "byte_size": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in _files(root)
        if path.relative_to(root).as_posix() not in exclude
    ]


def _version(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise PublicationContractError("application version must use major.minor.patch")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _validate_public_base_url(value: str, dataset_version: str) -> str:
    parsed = urlsplit(value)
    expected_suffix = f"/row-data/{dataset_version}/"
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not parsed.path.endswith(expected_suffix)
    ):
        raise PublicationContractError(
            f"public data URL must be an exact HTTPS origin path ending in {expected_suffix}"
        )
    return value


def _validate_app(app: Path, public_data_url: str, application_version: str) -> None:
    if not (app / "index.html").is_file() or not (app / "assets").is_dir():
        raise PublicationContractError("frontend build is missing index.html or assets")
    scripts = b"".join(path.read_bytes() for path in _files(app / "assets") if path.suffix == ".js")
    if public_data_url.encode() not in scripts:
        raise PublicationContractError("frontend build does not bind the declared public data URL")
    if application_version.encode() not in scripts:
        raise PublicationContractError(
            "frontend build does not contain the declared application version"
        )


def _validate_registry(path: Path, manifest: dict[str, object]) -> dict[str, object]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if (
        registry.get("registry_id") != manifest["metric_registry_version"]
        or registry.get("dataset_version") != manifest["dataset_version"]
        or registry.get("schema_version") != manifest["schema_version"]
    ):
        raise PublicationContractError(
            "compiled semantic registry is incompatible with row manifest"
        )
    return registry


def _data_dictionary(contract: PublicationContract) -> dict[str, object]:
    return {
        "contract_id": contract.contract_id,
        "dataset_version": contract.dataset_version,
        "schema_version": contract.schema_version,
        "grain": contract.grain,
        "fields": [
            {
                "name": field.public_name,
                "type": field.type,
                "null_rule": field.null_rule,
                "purpose": field.purpose,
                "linkability": field.linkability,
            }
            for field in contract.fields
            if field.status != "deny"
        ],
        "source_attribution": contract.source_attribution,
        "source_terms_url": contract.source_terms_url,
        "courtlistener_attribution": contract.courtlistener_attribution,
        "courtlistener_terms_url": contract.courtlistener_terms_url,
        "dataset_terms": contract.dataset_terms,
    }


def _scan_text_artifacts(root: Path) -> tuple[str, ...]:
    findings: list[str] = []
    for path in _files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in CREDENTIAL_PATTERNS.items():
            scanned = content
            if label == "private filesystem path":
                for literal in ALLOWED_LIBRARY_LITERALS:
                    scanned = scanned.replace(literal, "")
            if pattern.search(scanned):
                findings.append(f"{path.relative_to(root).as_posix()}: {label}")
    return tuple(findings)


def _scan_public_rows(row_mart: Path, allowed_fields: tuple[str, ...]) -> int:
    connection = duckdb.connect()
    try:
        scan = _scan_literal(row_mart)
        source = f"read_parquet({scan}, hive_partitioning = false)"
        columns = tuple(
            row[0] for row in connection.execute(f"describe select * from {source}").fetchall()
        )
        if set(columns) != set(allowed_fields) or len(columns) != len(allowed_fields):
            raise PublicationContractError("release candidate row schema does not match allowlist")
        text_columns = [
            row[0]
            for row in connection.execute(f"describe select * from {source}").fetchall()
            if "VARCHAR" in row[1]
        ]
        joined = " || chr(0) || ".join(
            f"coalesce(cast(\"{column}\" as varchar), '')" for column in text_columns
        )
        findings = connection.execute(
            f"""
            select count(*)
            from {source}
            where regexp_matches({joined}, '(?i)(api[_-]?key|password|access[_-]?token|client[_-]?secret)\\s*[:=]')
               or regexp_matches({joined}, '(?i)(/Users/|/home/|[A-Z]:\\\\Users\\\\)')
            """
        ).fetchone()
    finally:
        connection.close()
    return int(findings[0] if findings else 0)


def verify_release_candidate(root: Path) -> dict[str, object]:
    manifest_path = root / "release-manifest.json"
    if not manifest_path.is_file():
        raise PublicationContractError("release manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("files")
    actual = _inventory(root, exclude=frozenset({"release-manifest.json"}))
    if expected != actual:
        raise PublicationContractError("release candidate files do not match release manifest")
    total_bytes = sum(path.stat().st_size for path in _files(root))
    if total_bytes > RELEASE_BYTE_CEILING:
        raise PublicationContractError("release candidate exceeds byte ceiling")
    digest = hashlib.sha256(
        json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"file_count": len(actual) + 1, "total_bytes": total_bytes, "digest": digest}


def build_release_candidate(
    *,
    app: Path,
    row_mart: Path,
    semantic_registry: Path,
    package_json: Path,
    contract_path: Path,
    approved_cube: Path | None,
    public_data_url: str,
    output: Path,
) -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    if _inside(output, repository):
        raise PublicationContractError("release candidate must be written outside tracked Git")
    if output.exists():
        raise PublicationContractError("refusing to overwrite an existing release candidate")
    contract = load_publication_contract(contract_path)
    row_manifest = json.loads((row_mart / "manifest.json").read_text(encoding="utf-8"))
    validate_manifest(row_manifest, contract)
    application_version = json.loads(package_json.read_text(encoding="utf-8"))["version"]
    if _version(application_version)[0] != _version(row_manifest["minimum_app_version"])[
        0
    ] or _version(application_version) < _version(row_manifest["minimum_app_version"]):
        raise PublicationContractError("application version is incompatible with row manifest")
    if application_version != RELEASE_VERSION:
        raise PublicationContractError("application version does not match release version")
    public_data_url = _validate_public_base_url(public_data_url, contract.dataset_version)
    _validate_app(app, public_data_url, application_version)
    registry = _validate_registry(semantic_registry, row_manifest)
    validation = (
        validate_candidate(row_mart, row_manifest, contract, approved_cube)
        if approved_cube is not None
        else None
    )
    prohibited_rows = _scan_public_rows(row_mart, contract.allowed_fields) if approved_cube else 0
    if prohibited_rows:
        raise PublicationContractError("release candidate contains prohibited row values")

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.with_name(f".{output.name}.building")
    if stage.exists():
        raise PublicationContractError("release candidate staging path already exists")
    try:
        shutil.copytree(app, stage)
        data_root = stage / "row-data" / contract.dataset_version
        shutil.copytree(row_mart, data_root)
        shutil.copy2(semantic_registry, data_root / "metrics.v1.json")
        (data_root / "data-dictionary.json").write_text(
            json.dumps(_data_dictionary(contract), sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        text_findings = _scan_text_artifacts(stage)
        if text_findings:
            raise PublicationContractError(
                f"release candidate contains prohibited text artifacts: {text_findings[0]}"
            )
        files = _inventory(stage)
        release_manifest = {
            "release_version": RELEASE_VERSION,
            "application_version": application_version,
            "contract_id": contract.contract_id,
            "dataset_version": contract.dataset_version,
            "schema_version": contract.schema_version,
            "metric_registry_version": registry["registry_id"],
            "public_data_url": public_data_url,
            "entrypoint": "index.html",
            "row_manifest": f"row-data/{contract.dataset_version}/manifest.json",
            "semantic_registry": f"row-data/{contract.dataset_version}/metrics.v1.json",
            "data_dictionary": f"row-data/{contract.dataset_version}/data-dictionary.json",
            "files": files,
        }
        (stage / "release-manifest.json").write_text(
            json.dumps(release_manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        stage.rename(output)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    verified = verify_release_candidate(output)
    return {
        "status": "local_candidate_validated",
        "release_version": RELEASE_VERSION,
        "public_data_url": public_data_url,
        "row_validation": validation,
        "public_disallowed_value_count": prohibited_rows,
        **verified,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an immutable private row-release candidate."
    )
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--row-mart", type=Path, required=True)
    parser.add_argument("--semantic-registry", type=Path, required=True)
    parser.add_argument("--package-json", type=Path, required=True)
    parser.add_argument("--approved-cube", type=Path, required=True)
    parser.add_argument("--public-data-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path("config/public-row-mart-v1.toml"))
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = build_release_candidate(
        app=args.app,
        row_mart=args.row_mart,
        semantic_registry=args.semantic_registry,
        package_json=args.package_json,
        contract_path=args.contract,
        approved_cube=args.approved_cube,
        public_data_url=args.public_data_url,
        output=args.output,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.summary:
        if _inside(args.summary, Path(__file__).resolve().parents[1]):
            raise PublicationContractError("release summary must remain outside tracked Git")
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
