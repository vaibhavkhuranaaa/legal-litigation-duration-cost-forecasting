"""Shared trust-boundary controls for local release workflows."""

from __future__ import annotations

import bz2
import hashlib
import io
import re
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, TextIO

MAX_ARCHIVE_MEMBERS = 10_000
MAX_EXPANDED_BYTES = 128 * 1024**3
MAX_EXPANSION_RATIO = 100
MAX_LINE_BYTES = 4 * 1024**2
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SecurityBoundaryError(RuntimeError):
    """Raised when an untrusted input crosses a governed boundary."""


def expanded_byte_limit(compressed_bytes: int) -> int:
    if compressed_bytes <= 0:
        raise SecurityBoundaryError("compressed artifact must not be empty")
    return min(max(compressed_bytes * 64, 64 * 1024**2), MAX_EXPANDED_BYTES)


def validate_zip_budget(path: Path, archive: zipfile.ZipFile) -> int:
    members = [item for item in archive.infolist() if not item.is_dir()]
    if not members or len(members) > MAX_ARCHIVE_MEMBERS:
        raise SecurityBoundaryError("archive member count exceeds budget")
    limit = expanded_byte_limit(path.stat().st_size)
    total = 0
    for item in members:
        total += item.file_size
        if total > limit:
            raise SecurityBoundaryError("archive expanded bytes exceed budget")
        compressed = max(item.compress_size, 1)
        if item.file_size > 64 * 1024**2 and item.file_size / compressed > MAX_EXPANSION_RATIO:
            raise SecurityBoundaryError("archive expansion ratio exceeds budget")
    return limit


class LimitedReader(io.RawIOBase):
    def __init__(self, source: BinaryIO, limit: int) -> None:
        self.source = source
        self.limit = limit
        self.count = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray) -> int:
        remaining = self.limit - self.count
        if remaining <= 0:
            probe = self.source.read(1)
            if probe:
                raise SecurityBoundaryError("decompressed bytes exceed budget")
            return 0
        size = min(len(buffer), remaining + 1)
        chunk = self.source.read(size)
        if len(chunk) > remaining:
            raise SecurityBoundaryError("decompressed bytes exceed budget")
        buffer[: len(chunk)] = chunk
        self.count += len(chunk)
        return len(chunk)


@contextmanager
def bounded_bz2_text(path: Path, *, encoding: str = "utf-8") -> Iterator[TextIO]:
    with bz2.open(path, "rb") as compressed:
        limited = LimitedReader(compressed, expanded_byte_limit(path.stat().st_size))
        with io.TextIOWrapper(io.BufferedReader(limited), encoding=encoding, newline="") as text:
            yield text


def read_limited(source: BinaryIO, limit: int) -> bytes:
    payload = source.read(limit + 1)
    if len(payload) > limit:
        raise SecurityBoundaryError("archive member exceeds byte budget")
    return payload


def file_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def verify_manifest_artifact(source: Path, artifact: object) -> str:
    if not isinstance(artifact, dict):
        raise SecurityBoundaryError("manifest artifact must be an object")
    digest = artifact.get("sha256")
    size = artifact.get("bytes")
    if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
        raise SecurityBoundaryError("manifest SHA-256 is invalid")
    if not isinstance(size, int) or size <= 0:
        raise SecurityBoundaryError("manifest byte count is invalid")
    if not source.is_file() or source.stat().st_size != size:
        raise SecurityBoundaryError("source size does not match manifest")
    if file_sha256(source) != digest:
        raise SecurityBoundaryError("source SHA-256 does not match manifest")
    return digest


def require_outside_repository(path: Path) -> None:
    repository = Path(__file__).resolve().parents[2]
    try:
        path.resolve().relative_to(repository)
    except ValueError:
        return
    raise SecurityBoundaryError("output must be outside public repository")
