from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PATH = re.compile(r"(^|/)(?:\.project|private|internal)(?:/|$)", re.IGNORECASE)
FORBIDDEN_SUFFIX = {
    ".csv",
    ".tsv",
    ".parquet",
    ".xlsx",
    ".xls",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".sas7bdat",
    ".zip",
    ".ubj",
    ".onnx",
    ".joblib",
    ".tar",
    ".tgz",
}
STATE_NAME = re.compile(r"(^|/)terraform\.tfstate(?:\.|$)")
PRIVATE_ARTIFACT_NAME = re.compile(
    r"(^|/)(?:evaluation|baseline-evaluation|category-maps)\.json$", re.IGNORECASE
)


def public_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted({ROOT / line for line in result.stdout.splitlines() if (ROOT / line).is_file()})


def violations(paths: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if FORBIDDEN_PATH.search(relative):
            problems.append(f"private delivery path: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIX:
            problems.append(f"dataset or archive: {relative}")
        if STATE_NAME.search(relative):
            problems.append(f"Terraform state: {relative}")
        if PRIVATE_ARTIFACT_NAME.search(relative):
            problems.append(f"private evaluation artifact: {relative}")
        if path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            problems.append(f"oversized tracked file: {relative}")
    return problems


def main() -> int:
    problems = violations(public_files())
    if problems:
        raise SystemExit("\n".join(problems))
    print("public boundary: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
