from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from xml.etree import ElementTree

from litigation_planner.security import (
    SecurityBoundaryError,
    bounded_bz2_text,
    file_sha256,
    read_limited,
    validate_zip_budget,
)

CHUNK_BYTES = 1024 * 1024
RETRY_ATTEMPTS = 3
VALID_KINDS = {"csv_bz2", "pdf", "tabular_zip", "xlsx"}
SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
ALLOWED_SOURCE_HOSTS = {
    "www.fjc.gov",
    "www.uscourts.gov",
    "com-courtlistener-storage.s3-us-west-2.amazonaws.com",
}
MAX_XLSX_XML_BYTES = 32 * 1024**2


class AcquisitionError(RuntimeError):
    pass


def _validate_source_url(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_SOURCE_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
    ):
        raise AcquisitionError("source URL must use an approved HTTPS origin")
    return value


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _contained(root: Path, path: Path) -> Path:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise AcquisitionError("derived source path escapes approved root") from error
    return path


@dataclass(frozen=True)
class SourceSpec:
    id: str
    name: str
    url: str
    filename: str
    snapshot_cutoff: str
    kind: str
    max_bytes: int
    terms_url: str
    required_columns: tuple[str, ...] = ()


def load_registry(path: Path) -> dict[str, SourceSpec]:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise AcquisitionError("source registry version must be 1")
    sources: dict[str, SourceSpec] = {}
    for item in document.get("source", []):
        spec = SourceSpec(
            id=item["id"],
            name=item["name"],
            url=item["url"],
            filename=item["filename"],
            snapshot_cutoff=item["snapshot_cutoff"],
            kind=item["kind"],
            max_bytes=item["max_bytes"],
            terms_url=item["terms_url"],
            required_columns=tuple(item.get("required_columns", [])),
        )
        if spec.id in sources:
            raise AcquisitionError(f"duplicate source id: {spec.id}")
        if spec.kind not in VALID_KINDS:
            raise AcquisitionError(f"unsupported source kind: {spec.kind}")
        try:
            cutoff = date.fromisoformat(spec.snapshot_cutoff)
        except ValueError as error:
            raise AcquisitionError(f"invalid source boundary: {spec.id}") from error
        if (
            not SOURCE_ID_PATTERN.fullmatch(spec.id)
            or cutoff.isoformat() != spec.snapshot_cutoff
            or Path(spec.filename).name != spec.filename
            or spec.max_bytes <= 0
        ):
            raise AcquisitionError(f"invalid source boundary: {spec.id}")
        _validate_source_url(spec.url)
        sources[spec.id] = spec
    if not sources:
        raise AcquisitionError("source registry is empty")
    return sources


def _download_once(spec: SourceSpec, partial: Path) -> dict[str, str]:
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "federal-civil-litigation-planner/0.1"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(_validate_source_url(spec.url), headers=headers)
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    with opener.open(request, timeout=120) as response:
        _validate_source_url(response.geturl())
        status = getattr(response, "status", 200)
        if offset and status != 206:
            raise AcquisitionError("source did not honor byte-range resume")
        length = response.headers.get("Content-Length")
        if length and offset + int(length) > spec.max_bytes:
            raise AcquisitionError(f"source exceeds {spec.max_bytes}-byte cap")
        mode = "ab" if offset else "wb"
        with partial.open(mode) as output:
            size = offset
            while chunk := response.read(CHUNK_BYTES):
                size += len(chunk)
                if size > spec.max_bytes:
                    raise AcquisitionError(f"source exceeds {spec.max_bytes}-byte cap")
                output.write(chunk)
        return {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
        }


def download(spec: SourceSpec, destination: Path, attempts: int = RETRY_ATTEMPTS) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    last_error: OSError | URLError | None = None
    for attempt in range(attempts):
        try:
            headers = _download_once(spec, partial)
            os.replace(partial, destination)
            return headers
        except AcquisitionError:
            raise
        except (OSError, URLError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise AcquisitionError(f"source failed after {attempts} attempts: {last_error}")


def _schema_result(summary: dict[str, object]) -> dict[str, object]:
    encoded = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
    return {"fingerprint_sha256": hashlib.sha256(encoded).hexdigest(), "summary": summary}


def _validate_csv_bz2(path: Path, required: tuple[str, ...]) -> dict[str, object]:
    try:
        with bounded_bz2_text(path) as source:
            header = next(csv.reader(source))
            while source.read(CHUNK_BYTES):
                pass
    except (OSError, EOFError, UnicodeDecodeError, csv.Error, SecurityBoundaryError) as error:
        raise AcquisitionError(f"invalid bzip2 CSV: {error}") from error
    missing = sorted(set(required).difference(header))
    if missing:
        raise AcquisitionError(f"missing required columns: {missing}")
    return _schema_result({"kind": "csv", "encoding": "utf-8", "delimiter": ",", "columns": header})


def _validate_pdf(path: Path) -> dict[str, object]:
    with path.open("rb") as source:
        first = source.readline(32).strip().decode("ascii", errors="replace")
        source.seek(max(0, path.stat().st_size - 1024))
        tail = source.read()
    if not first.startswith("%PDF-") or b"%%EOF" not in tail:
        raise AcquisitionError("invalid PDF envelope")
    return _schema_result({"kind": "document", "format": first})


def _validate_tabular_zip(
    path: Path, required: tuple[str, ...]
) -> tuple[dict[str, object], list[str]]:
    try:
        with zipfile.ZipFile(path) as archive:
            validate_zip_budget(path, archive)
            bad_member = archive.testzip()
            if bad_member:
                raise AcquisitionError(f"corrupt ZIP member: {bad_member}")
            members = sorted(item.filename for item in archive.infolist() if not item.is_dir())
            tabular = next(
                (name for name in members if name.lower().endswith((".txt", ".tsv", ".csv"))), None
            )
            if not tabular:
                raise AcquisitionError("ZIP has no tabular member")
            with archive.open(tabular) as source:
                line = source.readline(1024 * 1024)
    except (OSError, SecurityBoundaryError, zipfile.BadZipFile) as error:
        raise AcquisitionError(f"invalid ZIP: {error}") from error
    text = line.decode("utf-8-sig", errors="replace").rstrip("\r\n")
    delimiter = "\t" if "\t" in text else ","
    header = next(csv.reader([text], delimiter=delimiter))
    if len(header) < 2:
        raise AcquisitionError("tabular ZIP header has fewer than two columns")
    missing = sorted(set(required).difference(header))
    if missing:
        raise AcquisitionError(f"missing required columns: {missing}")
    schema = _schema_result(
        {
            "kind": "delimited",
            "header_encoding": "ascii-compatible",
            "delimiter": "tab" if delimiter == "\t" else "comma",
            "member": tabular,
            "columns": header,
        }
    )
    return schema, members


def _xlsx_cell_values(archive: zipfile.ZipFile) -> tuple[list[str], dict[str, list[list[str]]]]:
    namespaces = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    }
    shared: list[str] = []
    if "xl/sharedStrings.xml" in archive.namelist():
        with archive.open("xl/sharedStrings.xml") as source:
            root = ElementTree.fromstring(read_limited(source, MAX_XLSX_XML_BYTES))
        for item in root.findall("main:si", namespaces):
            shared.append(
                "".join(node.text or "" for node in item.iterfind(".//main:t", namespaces))
            )
    with archive.open("xl/workbook.xml") as source:
        workbook = ElementTree.fromstring(read_limited(source, MAX_XLSX_XML_BYTES))
    sheet_names = [node.attrib["name"] for node in workbook.findall(".//main:sheet", namespaces)]
    previews: dict[str, list[list[str]]] = {}
    sheet_files = sorted(
        name
        for name in archive.namelist()
        if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
    )
    for index, filename in enumerate(sheet_files):
        with archive.open(filename) as source:
            root = ElementTree.fromstring(read_limited(source, MAX_XLSX_XML_BYTES))
        rows: list[list[str]] = []
        for row in root.findall(".//main:sheetData/main:row", namespaces)[:10]:
            values: list[str] = []
            for cell in row.findall("main:c", namespaces):
                value = cell.find("main:v", namespaces)
                raw = value.text if value is not None and value.text is not None else ""
                if cell.attrib.get("t") == "s" and raw:
                    raw = shared[int(raw)]
                values.append(raw)
            if any(values):
                rows.append(values)
        name = sheet_names[index] if index < len(sheet_names) else filename
        previews[name] = rows
    return sheet_names, previews


def _validate_xlsx(path: Path) -> tuple[dict[str, object], list[str]]:
    try:
        with zipfile.ZipFile(path) as archive:
            validate_zip_budget(path, archive)
            bad_member = archive.testzip()
            if bad_member:
                raise AcquisitionError(f"corrupt XLSX member: {bad_member}")
            required = {"[Content_Types].xml", "xl/workbook.xml"}
            if missing := sorted(required.difference(archive.namelist())):
                raise AcquisitionError(f"XLSX missing members: {missing}")
            members = sorted(item.filename for item in archive.infolist() if not item.is_dir())
            sheet_names, previews = _xlsx_cell_values(archive)
    except (
        OSError,
        ValueError,
        IndexError,
        SecurityBoundaryError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
    ) as error:
        raise AcquisitionError(f"invalid XLSX: {error}") from error
    return _schema_result({"kind": "xlsx", "sheets": sheet_names, "preview": previews}), members


def validate_artifact(spec: SourceSpec, path: Path) -> dict[str, object]:
    size = path.stat().st_size
    if not size or size > spec.max_bytes:
        raise AcquisitionError(f"artifact size {size} violates source cap")
    members: list[str] = []
    if spec.kind == "csv_bz2":
        schema = _validate_csv_bz2(path, spec.required_columns)
    elif spec.kind == "pdf":
        schema = _validate_pdf(path)
    elif spec.kind == "tabular_zip":
        schema, members = _validate_tabular_zip(path, spec.required_columns)
    else:
        schema, members = _validate_xlsx(path)
    return {
        "status": "valid",
        "archive_members": members,
        "schema": schema,
    }


def acquire_source(
    spec: SourceSpec,
    data_root: Path,
    manifest_dir: Path,
    existing: Path | None = None,
    provenance_manifest: Path | None = None,
) -> Path:
    target = existing or _contained(
        data_root, data_root / spec.id / spec.snapshot_cutoff / spec.filename
    )
    if not existing and not target.exists():
        candidates = sorted(target.parent.glob(f"????????????????-{spec.filename}"))
        if len(candidates) > 1:
            raise AcquisitionError(f"multiple immutable objects found: {spec.id}")
        if candidates:
            target = candidates[0]
    method = "retained" if existing or target.exists() else "downloaded"
    promote = not existing and target.name == spec.filename
    headers: dict[str, str] = {}
    if not target.exists():
        headers = download(spec, target)
    validation = validate_artifact(spec, target)
    sha256 = file_sha256(target)
    if promote:
        immutable = target.with_name(f"{sha256[:16]}-{spec.filename}")
        if immutable.exists() and file_sha256(immutable) != sha256:
            raise AcquisitionError(f"immutable object conflict: {immutable.name}")
        if not immutable.exists():
            os.replace(target, immutable)
        target = immutable
    try:
        storage_key = target.resolve().relative_to(data_root.resolve()).as_posix()
    except ValueError:
        storage_key = f"retained:{target.name}"
    manifest: dict[str, object] = {
        "version": 1,
        "source_id": spec.id,
        "source_name": spec.name,
        "source_url": spec.url,
        "terms_url": spec.terms_url,
        "snapshot_cutoff": spec.snapshot_cutoff,
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "retrieval_method": method,
        "http": headers,
        "artifact": {
            "storage_key": storage_key,
            "bytes": target.stat().st_size,
            "sha256": sha256,
        },
        "validation": validation,
    }
    if provenance_manifest:
        prior = json.loads(provenance_manifest.read_text(encoding="utf-8"))
        manifest["retained_provenance"] = {
            "manifest_path": str(provenance_manifest.resolve()),
            "retrieved_at_utc": prior.get("retrieved_at_utc"),
            "source_etag": prior.get("source_etag"),
            "sha256": prior.get("sha256"),
        }
        prior_sha = prior.get("sha256")
        if prior_sha and prior_sha != manifest["artifact"]["sha256"]:
            raise AcquisitionError(f"retained checksum mismatch: {spec.id}")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _contained(
        manifest_dir,
        manifest_dir / f"{spec.id}-{spec.snapshot_cutoff}-{sha256[:16]}.json",
    )
    content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        if prior.get("artifact", {}).get("sha256") != sha256:
            raise AcquisitionError(f"immutable manifest conflict: {manifest_path.name}")
        return manifest_path
    manifest_path.write_text(content, encoding="utf-8")
    return manifest_path


def _keyed_paths(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        key, separator, path = value.partition("=")
        if not separator or not key or not path:
            raise AcquisitionError(f"expected SOURCE_ID=PATH, got: {value}")
        result[key] = Path(path)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Acquire pinned public court source artifacts.")
    parser.add_argument("--registry", type=Path, default=Path("config/sources.toml"))
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifest-dir", type=Path, required=True)
    parser.add_argument("--existing", action="append", default=[], metavar="SOURCE_ID=PATH")
    parser.add_argument(
        "--provenance-manifest",
        action="append",
        default=[],
        metavar="SOURCE_ID=PATH",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    registry = load_registry(args.registry)
    selected = args.source or list(registry)
    unknown = sorted(set(selected).difference(registry))
    if unknown:
        raise AcquisitionError(f"unknown source ids: {unknown}")
    existing = _keyed_paths(args.existing)
    provenance = _keyed_paths(args.provenance_manifest)
    repository = Path(__file__).resolve().parents[2]
    for private_path in (args.data_root, args.manifest_dir):
        try:
            private_path.resolve().relative_to(repository)
        except ValueError:
            continue
        raise AcquisitionError("raw artifacts and manifests must be outside public repository")
    manifests: list[Path] = []
    for source_id in selected:
        manifest = acquire_source(
            registry[source_id],
            args.data_root,
            args.manifest_dir,
            existing.get(source_id),
            provenance.get(source_id),
        )
        manifests.append(manifest)
        print(manifest)
    source_set = {
        "version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "sources": [
            {
                "manifest": manifest.name,
                "sha256": file_sha256(manifest),
            }
            for manifest in manifests
        ],
    }
    set_content = json.dumps(source_set, indent=2, sort_keys=True) + "\n"
    set_digest = hashlib.sha256(set_content.encode()).hexdigest()
    set_path = args.manifest_dir / f"m2-source-set-{set_digest[:16]}.json"
    if not set_path.exists():
        set_path.write_text(set_content, encoding="utf-8")
    print(set_path)
    return 0
