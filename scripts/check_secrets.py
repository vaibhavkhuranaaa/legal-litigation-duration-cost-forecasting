"""Fail when public source files contain credential-shaped literals."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "node_modules", "dist", "target", "tmp", "data"}
SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".toml", ".yml", ".yaml", ".md", ".sql"}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{30,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
}


def scan() -> list[str]:
    findings: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        if any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
    return findings


if __name__ == "__main__":
    results = scan()
    if results:
        raise SystemExit("credential-shaped literals found:\n" + "\n".join(results))
    print("secret scan passed: 0 credential-shaped literals")
