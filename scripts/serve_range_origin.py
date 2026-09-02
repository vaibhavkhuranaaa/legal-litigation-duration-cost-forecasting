from __future__ import annotations

import argparse
import json
import mimetypes
import re
import threading
from datetime import UTC, datetime
from email.utils import formatdate
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

RANGE_PATTERN = re.compile(r"bytes=(\d*)-(\d*)$")


class RangeOriginHandler(BaseHTTPRequestHandler):
    server: RangeOriginServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def end_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin in self.server.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Range")
            self.send_header(
                "Access-Control-Expose-Headers",
                "Accept-Ranges, Content-Length, Content-Range, Content-Type, ETag",
            )
            self.send_header("Vary", "Origin")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        super().end_headers()

    def _reject_unapproved_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None or origin in self.server.allowed_origins:
            return False
        self.send_error(HTTPStatus.FORBIDDEN, "browser origin is not approved")
        return True

    def do_OPTIONS(self) -> None:
        if self.headers.get("Origin") not in self.server.allowed_origins:
            self.send_error(HTTPStatus.FORBIDDEN, "browser origin is not approved")
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:
        if self._reject_unapproved_origin():
            return
        self._serve(send_body=False)

    def do_GET(self) -> None:
        if self._reject_unapproved_origin():
            return
        self._serve(send_body=True)

    def _resolve_file(self) -> Path | None:
        requested = unquote(urlsplit(self.path).path).lstrip("/")
        if not requested:
            return None
        candidate = (self.server.root / requested).resolve()
        try:
            candidate.relative_to(self.server.root)
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def _parse_range(self, size: int) -> tuple[int, int] | None:
        header = self.headers.get("Range")
        if not header:
            return None
        match = RANGE_PATTERN.fullmatch(header.strip())
        if not match:
            raise ValueError("unsupported byte range")
        start_text, end_text = match.groups()
        if not start_text:
            length = int(end_text)
            if length <= 0:
                raise ValueError("invalid suffix range")
            return max(size - length, 0), size - 1
        start = int(start_text)
        end = min(int(end_text), size - 1) if end_text else size - 1
        if start >= size or start > end:
            raise ValueError("range outside file")
        return start, end

    def _serve(self, *, send_body: bool) -> None:
        file = self._resolve_file()
        if file is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        size = file.stat().st_size
        try:
            requested_range = self._parse_range(size)
        except ValueError:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            self.server.record(self, HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, 0, size)
            return

        start, end = requested_range or (0, size - 1)
        status = HTTPStatus.PARTIAL_CONTENT if requested_range else HTTPStatus.OK
        content_length = end - start + 1
        content_type = (
            "application/vnd.apache.parquet"
            if file.suffix == ".parquet"
            else mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("ETag", f'"m17-{size:x}-{file.stat().st_mtime_ns:x}"')
        self.send_header("Last-Modified", formatdate(file.stat().st_mtime, usegmt=True))
        if requested_range:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        bytes_sent = 0
        if send_body:
            with file.open("rb") as handle:
                handle.seek(start)
                remaining = content_length
                while remaining:
                    chunk = handle.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
                    bytes_sent += len(chunk)
        self.server.record(self, status, bytes_sent, size)


class RangeOriginServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        root: Path,
        log_path: Path,
        allowed_origins: frozenset[str],
    ):
        super().__init__(address, RangeOriginHandler)
        self.root = root.resolve()
        self.log_path = log_path.resolve()
        self.allowed_origins = allowed_origins
        self._log_lock = threading.Lock()

    def record(
        self, request: RangeOriginHandler, status: HTTPStatus, bytes_sent: int, file_size: int
    ) -> None:
        entry = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "method": request.command,
            "path": urlsplit(request.path).path,
            "query_present": bool(urlsplit(request.path).query),
            "range": request.headers.get("Range"),
            "status": int(status),
            "bytes_sent": bytes_sent,
            "file_size": file_size,
            "user_agent": request.headers.get("User-Agent", ""),
        }
        encoded = json.dumps(entry, sort_keys=True) + "\n"
        with self._log_lock, self.log_path.open("a", encoding="utf-8") as stream:
            stream.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve private M17 files from a local byte origin."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--allow-origin",
        action="append",
        required=True,
        help="Exact browser origin allowed to read the private mart; repeat as needed.",
    )
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("M17 range origin must remain bound to loopback")
    if not args.root.is_dir():
        raise ValueError("range origin root must exist")
    allowed_origins = frozenset(args.allow_origin)
    for origin in allowed_origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("allowed origins must be exact HTTP(S) origins")
    args.log.parent.mkdir(parents=True, exist_ok=True)
    server = RangeOriginServer((args.host, args.port), args.root, args.log, allowed_origins)
    print(f"M17 range origin listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
