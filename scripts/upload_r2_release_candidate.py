from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from litigation_planner.publication_contract import PublicationContractError
from scripts.build_row_release_candidate import verify_release_candidate

BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
PREFIX_PATTERN = re.compile(r"^releases/m22-[a-f0-9]{64}$")
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"
CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".parquet": "application/vnd.apache.parquet",
    ".wasm": "application/wasm",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


@dataclass(frozen=True)
class Upload:
    relative_path: str
    source: Path
    byte_size: int
    sha256: str
    content_type: str
    cache_control: str


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _content_type(path: Path) -> str:
    return CONTENT_TYPES.get(
        path.suffix.lower(),
        mimetypes.guess_type(path.name)[0] or "application/octet-stream",
    )


def upload_plan(
    candidate: Path, bucket: str, prefix: str
) -> tuple[dict[str, object], list[Upload]]:
    repository = Path(__file__).resolve().parents[1]
    if _inside(candidate, repository):
        raise PublicationContractError("R2 candidate must remain outside tracked Git")
    if not BUCKET_PATTERN.fullmatch(bucket):
        raise PublicationContractError("R2 bucket name is invalid")
    if not PREFIX_PATTERN.fullmatch(prefix):
        raise PublicationContractError("R2 release prefix must bind an exact M22 candidate digest")
    verification = verify_release_candidate(candidate)
    release_manifest_path = candidate / "release-manifest.json"
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    declared = list(release_manifest["files"])
    declared.append(
        {
            "path": "release-manifest.json",
            "byte_size": release_manifest_path.stat().st_size,
            "sha256": _sha256(release_manifest_path),
        }
    )
    uploads: list[Upload] = []
    for item in declared:
        relative = str(item["path"])
        source = candidate / relative
        if (
            not source.is_file()
            or source.is_symlink()
            or _sha256(source) != item["sha256"]
            or source.stat().st_size != item["byte_size"]
        ):
            raise PublicationContractError(f"candidate upload input drifted: {relative}")
        uploads.append(
            Upload(
                relative_path=relative,
                source=source,
                byte_size=source.stat().st_size,
                sha256=str(item["sha256"]),
                content_type=_content_type(source),
                cache_control="no-cache" if relative == "index.html" else IMMUTABLE_CACHE,
            )
        )
    if len(uploads) != verification["file_count"]:
        raise PublicationContractError("candidate upload inventory is incomplete")
    return verification, uploads


def upload_candidate(
    *,
    candidate: Path,
    bucket: str,
    prefix: str,
    wrangler: Path,
    node: Path | None,
    execute: bool,
    attempts: int,
    transport: str,
    account_id: str,
) -> dict[str, object]:
    verification, uploads = upload_plan(candidate, bucket, prefix)
    if execute and not wrangler.is_file():
        raise PublicationContractError("Wrangler executable is unavailable")
    if execute and node is not None and not node.is_file():
        raise PublicationContractError("requested Node executable is unavailable")
    if attempts < 1 or attempts > 8:
        raise PublicationContractError("upload attempts must be between 1 and 8")
    if transport not in {"file", "pipe"}:
        raise PublicationContractError("upload transport must be file or pipe")
    if not re.fullmatch(r"[a-f0-9]{32}", account_id):
        raise PublicationContractError("Cloudflare account ID must be 32 lowercase hex characters")
    environment = {**os.environ, "CLOUDFLARE_ACCOUNT_ID": account_id}
    retried_puts = 0
    for upload in uploads:
        command = [
            *([str(node), str(wrangler)] if node is not None else [str(wrangler)]),
            "r2",
            "object",
            "put",
            f"{bucket}/{prefix}/{upload.relative_path}",
            *(["--file", str(upload.source)] if transport == "file" else ["--pipe"]),
            "--content-type",
            upload.content_type,
            "--cache-control",
            upload.cache_control,
            "--storage-class",
            "Standard",
            "--remote",
            "--force",
        ]
        if execute:
            for attempt in range(1, attempts + 1):
                with upload.source.open("rb") as upload_body:
                    completed = subprocess.run(
                        command,
                        check=False,
                        stdin=upload_body if transport == "pipe" else None,
                        capture_output=True,
                        text=True,
                        env=environment,
                    )
                if not completed.returncode:
                    break
                detail = completed.stderr.strip() or completed.stdout.strip()
                transient = (
                    "fetch failed" in detail.lower() or "connectivity issue" in detail.lower()
                )
                if not transient or attempt == attempts:
                    raise PublicationContractError(
                        f"R2 upload failed for {upload.relative_path}: {detail}"
                    )
                retried_puts += 1
                time.sleep(attempt)
    return {
        "status": "uploaded" if execute else "validated_dry_run",
        "bucket": bucket,
        "cloudflare_account_id": account_id,
        "prefix": prefix,
        "candidate_digest": verification["digest"],
        "object_count": len(uploads),
        "retried_puts": retried_puts,
        "transport": transport,
        "total_bytes": sum(upload.byte_size for upload in uploads),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload one verified M22 candidate to private R2.")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--wrangler", type=Path, required=True)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--transport", choices=("file", "pipe"), default="file")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = upload_candidate(
        candidate=args.candidate,
        bucket=args.bucket,
        prefix=args.prefix,
        wrangler=args.wrangler,
        node=args.node,
        execute=args.execute,
        attempts=args.attempts,
        transport=args.transport,
        account_id=args.account_id,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.summary:
        if _inside(args.summary, Path(__file__).resolve().parents[1]):
            raise PublicationContractError("upload summary must remain outside tracked Git")
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
