from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote, urlsplit

from litigation_planner.publication_contract import PublicationContractError
from scripts.upload_r2_release_candidate import _inside, upload_plan

EXPECTED_HOSTS = frozenset(
    {
        "legal-litigation-row-candidate.gp-access-planner.workers.dev",
        "legal-litigation-row-data.gp-access-planner.workers.dev",
    }
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _headers(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="iso-8859-1").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip().lower()] = value.strip()
    return values


def _curl(
    url: str,
    *,
    output: Path,
    headers: Path,
    method: str = "GET",
    request_headers: tuple[str, ...] = (),
) -> tuple[int, str, int, dict[str, str]]:
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--http1.1",
        "--retry",
        "4",
        "--retry-all-errors",
        "--request",
        method,
        "--output",
        str(output),
        "--dump-header",
        str(headers),
    ]
    for header in request_headers:
        command.extend(["--header", header])
    command.extend(["--write-out", "%{http_code}\n%{url_effective}\n%{size_download}", url])
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PublicationContractError(f"live candidate request failed: {detail}")
    lines = completed.stdout.splitlines()
    if len(lines) != 3:
        raise PublicationContractError("live candidate returned an invalid curl receipt")
    return int(lines[0]), lines[1], int(float(lines[2])), _headers(headers)


def verify_live_candidate(
    *, candidate: Path, bucket: str, prefix: str, base_url: str
) -> dict[str, object]:
    verification, uploads = upload_plan(candidate, bucket, prefix)
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in EXPECTED_HOSTS
        or parsed.path not in {"", "/"}
    ):
        raise PublicationContractError("live verification URL must be an approved release origin")
    verified_bytes = 0
    with tempfile.TemporaryDirectory(prefix="m22-live-verify-") as temporary_directory:
        temporary = Path(temporary_directory)
        for index, upload in enumerate(uploads):
            output = temporary / f"object-{index}"
            response_headers = temporary / f"headers-{index}"
            encoded = quote(upload.relative_path, safe="/-._~=")
            url = f"{base_url.rstrip('/')}/{encoded}"
            status, effective_url, downloaded, headers = _curl(
                url,
                output=output,
                headers=response_headers,
            )
            if status != 200 or effective_url != url:
                raise PublicationContractError(
                    f"live candidate redirected or failed: {upload.relative_path}"
                )
            if downloaded != upload.byte_size or output.stat().st_size != upload.byte_size:
                raise PublicationContractError(
                    f"live candidate size mismatch: {upload.relative_path}"
                )
            if _sha256(output) != upload.sha256:
                raise PublicationContractError(
                    f"live candidate digest mismatch: {upload.relative_path}"
                )
            expected_cache = (
                "no-cache" if upload.relative_path == "index.html" else upload.cache_control
            )
            if headers.get("cache-control") != expected_cache:
                raise PublicationContractError(
                    f"live candidate cache mismatch: {upload.relative_path}"
                )
            if upload.relative_path.endswith(".parquet"):
                if headers.get("content-type") != "application/vnd.apache.parquet":
                    raise PublicationContractError("live Parquet MIME type is invalid")
                if headers.get("accept-ranges") != "bytes":
                    raise PublicationContractError("live Parquet range support is absent")
            verified_bytes += downloaded

        parquet_path = "row-data/fjc-civil-2026-03-31.v1/filing_year=2025/part-00000.parquet"
        parquet_url = f"{base_url.rstrip('/')}/{parquet_path}"
        range_output = temporary / "range"
        range_headers = temporary / "range-headers"
        status, effective_url, downloaded, headers = _curl(
            parquet_url,
            output=range_output,
            headers=range_headers,
            request_headers=("Origin: https://vaibhavkhuranaaa.github.io", "Range: bytes=0-3"),
        )
        if (
            status != 206
            or effective_url != parquet_url
            or downloaded != 4
            or range_output.read_bytes() != b"PAR1"
            or headers.get("content-range") != "bytes 0-3/6444047"
            or headers.get("access-control-allow-origin") != "https://vaibhavkhuranaaa.github.io"
        ):
            raise PublicationContractError("live candidate range or CORS behavior failed")

        cors_output = temporary / "cors"
        cors_headers = temporary / "cors-headers"
        status, _, _, headers = _curl(
            parquet_url,
            output=cors_output,
            headers=cors_headers,
            method="OPTIONS",
            request_headers=(
                "Origin: https://vaibhavkhuranaaa.github.io",
                "Access-Control-Request-Method: GET",
                "Access-Control-Request-Headers: Range",
            ),
        )
        if (
            status != 204
            or headers.get("access-control-allow-origin") != "https://vaibhavkhuranaaa.github.io"
            or headers.get("access-control-allow-headers") != "Range"
        ):
            raise PublicationContractError("live candidate preflight failed")

        closed_output = temporary / "closed"
        closed_headers = temporary / "closed-headers"
        status, _, _, _ = _curl(
            f"{base_url.rstrip('/')}/__m22-upload/index.html",
            output=closed_output,
            headers=closed_headers,
            method="POST",
        )
        if status != 404:
            raise PublicationContractError("temporary upload route remains reachable")

    return {
        "status": "verified",
        "base_url": base_url.rstrip("/"),
        "candidate_digest": verification["digest"],
        "object_count": len(uploads),
        "verified_bytes": verified_bytes,
        "redirect_count": 0,
        "sha256_mismatches": 0,
        "range_cors_pass": True,
        "upload_route_closed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify every live M22 candidate object and boundary."
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = verify_live_candidate(
        candidate=args.candidate,
        bucket=args.bucket,
        prefix=args.prefix,
        base_url=args.base_url,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.summary:
        if _inside(args.summary, Path(__file__).resolve().parents[1]):
            raise PublicationContractError(
                "live verification summary must remain outside tracked Git"
            )
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
