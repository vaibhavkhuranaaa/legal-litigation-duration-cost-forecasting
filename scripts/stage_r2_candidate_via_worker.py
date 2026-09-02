from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote, urlsplit

from litigation_planner.publication_contract import PublicationContractError
from scripts.upload_r2_release_candidate import _inside, upload_plan

EXPECTED_HOST = "legal-litigation-row-candidate.gp-access-planner.workers.dev"
MULTIPART_PART_BYTES = 5 * 1024 * 1024


def _command_prefix(node: Path | None, wrangler: Path) -> list[str]:
    return [str(node), str(wrangler)] if node is not None else [str(wrangler)]


def _run(command: list[str], *, environment: dict[str, str], input_text: str | None = None) -> None:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        env=environment,
        input=input_text,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PublicationContractError(f"command failed: {detail}")


def _curl(
    arguments: list[str],
    *,
    curl_config: str,
    expected_status: str,
    retry: bool,
) -> str:
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--http1.1",
        "--header",
        "Expect:",
    ]
    if retry:
        command.extend(["--retry", "5", "--retry-all-errors"])
    command.extend([*arguments, "--write-out", "\n%{http_code}", "--config", "-"])
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        input=curl_config,
        text=True,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise PublicationContractError(f"candidate Worker request failed: {detail}")
    response_body, separator, status = completed.stdout.rpartition("\n")
    if not separator or status.strip() != expected_status:
        raise PublicationContractError(
            f"candidate Worker returned HTTP {status.strip() or 'unknown'}, expected {expected_status}"
        )
    return response_body


def _last_json_object(response_body: str) -> dict[str, object]:
    for offset in range(len(response_body) - 1, -1, -1):
        if response_body[offset] != "{":
            continue
        try:
            value = json.loads(response_body[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise PublicationContractError("candidate Worker response did not contain a JSON receipt")


def _direct_upload(*, source: Path, target: str, curl_config: str) -> None:
    _curl(
        ["--request", "PUT", "--upload-file", str(source), target],
        curl_config=curl_config,
        expected_status="201",
        retry=True,
    )


def _multipart_upload(
    *, source: Path, worker_url: str, encoded_path: str, curl_config: str
) -> None:
    target_root = f"{worker_url.rstrip('/')}/__m22-multipart"
    start_body = _curl(
        [
            "--request",
            "POST",
            "--data-binary",
            "",
            f"{target_root}/start/{encoded_path}",
        ],
        curl_config=curl_config,
        expected_status="200",
        retry=True,
    )
    upload_id = _last_json_object(start_body).get("upload_id")
    if not isinstance(upload_id, str) or not upload_id:
        raise PublicationContractError("candidate Worker returned an invalid multipart ID")
    parts: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="m22-r2-part-") as temporary_directory:
        part_path = Path(temporary_directory) / "part.bin"
        with source.open("rb") as source_handle:
            part_number = 1
            while chunk := source_handle.read(MULTIPART_PART_BYTES):
                part_path.write_bytes(chunk)
                query = f"uploadId={quote(upload_id, safe='-._~')}&partNumber={part_number}"
                part_body = _curl(
                    [
                        "--request",
                        "PUT",
                        "--upload-file",
                        str(part_path),
                        f"{target_root}/part/{encoded_path}?{query}",
                    ],
                    curl_config=curl_config,
                    expected_status="200",
                    retry=True,
                )
                part = _last_json_object(part_body)
                if part.get("partNumber") != part_number or not isinstance(part.get("etag"), str):
                    raise PublicationContractError(
                        "candidate Worker returned an invalid part receipt"
                    )
                parts.append({"etag": part["etag"], "partNumber": part_number})
                part_number += 1
    receipt = json.dumps({"parts": parts}, separators=(",", ":"))
    query = f"uploadId={quote(upload_id, safe='-._~')}"
    _curl(
        [
            "--request",
            "POST",
            "--header",
            "Content-Type: application/json",
            "--data-binary",
            receipt,
            f"{target_root}/complete/{encoded_path}?{query}",
        ],
        curl_config=curl_config,
        expected_status="201",
        retry=False,
    )


def stage_candidate(
    *,
    candidate: Path,
    bucket: str,
    prefix: str,
    wrangler: Path,
    node: Path | None,
    config: Path,
    account_id: str,
    worker_url: str,
    execute: bool,
) -> dict[str, object]:
    verification, uploads = upload_plan(candidate, bucket, prefix)
    parsed_url = urlsplit(worker_url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != EXPECTED_HOST
        or parsed_url.path not in {"", "/"}
    ):
        raise PublicationContractError(
            "upload Worker URL must be the exact approved candidate origin"
        )
    if not config.is_file() or not wrangler.is_file() or (node is not None and not node.is_file()):
        raise PublicationContractError("upload Worker toolchain is incomplete")
    if not re.fullmatch(r"[a-f0-9]{32}", account_id):
        raise PublicationContractError("Cloudflare account ID must be 32 lowercase hex characters")
    environment = {**os.environ, "CLOUDFLARE_ACCOUNT_ID": account_id}
    if execute:
        prefix_command = _command_prefix(node, wrangler)
        _run(
            [*prefix_command, "deploy", "--config", str(config)],
            environment=environment,
        )
        upload_token = secrets.token_urlsafe(48)
        _run(
            [*prefix_command, "secret", "put", "UPLOAD_TOKEN", "--config", str(config)],
            environment=environment,
            input_text=upload_token,
        )
        curl_config = f'header = "Authorization: Bearer {upload_token}"\n'
        for upload in uploads:
            encoded_path = quote(upload.relative_path, safe="/-._~=")
            if upload.byte_size > MULTIPART_PART_BYTES:
                _multipart_upload(
                    source=upload.source,
                    worker_url=worker_url,
                    encoded_path=encoded_path,
                    curl_config=curl_config,
                )
            else:
                _direct_upload(
                    source=upload.source,
                    target=f"{worker_url.rstrip('/')}/__m22-upload/{encoded_path}",
                    curl_config=curl_config,
                )
    return {
        "status": "uploaded" if execute else "validated_dry_run",
        "bucket": bucket,
        "candidate_digest": verification["digest"],
        "cloudflare_account_id": account_id,
        "object_count": len(uploads),
        "prefix": prefix,
        "total_bytes": sum(upload.byte_size for upload in uploads),
        "transport": "authenticated_candidate_worker",
        "worker_url": worker_url.rstrip("/"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage one exact M22 candidate through an upload-only Worker."
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--wrangler", type=Path, required=True)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--worker-url", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = stage_candidate(
        candidate=args.candidate,
        bucket=args.bucket,
        prefix=args.prefix,
        wrangler=args.wrangler,
        node=args.node,
        config=args.config,
        account_id=args.account_id,
        worker_url=args.worker_url,
        execute=args.execute,
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
