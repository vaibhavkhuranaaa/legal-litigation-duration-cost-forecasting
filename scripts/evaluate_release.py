"""Cold-start-independent checks for the pinned local release contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from litigation_planner.api import app
from litigation_planner.demo import build_demo_database

ROOT = Path(__file__).resolve().parents[1]


def evaluate() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        first = Path(directory) / "one.sqlite"
        second = Path(directory) / "two.sqlite"
        build_demo_database(first)
        build_demo_database(second)
        seed_replay = (
            hashlib.sha256(first.read_bytes()).digest()
            == hashlib.sha256(second.read_bytes()).digest()
        )
    client = TestClient(app)
    readiness = client.get("/v1/readiness").json()
    provenance = client.get("/v1/provenance").json()
    explorer = client.get("/v1/population-explorer").json()
    forecast = client.post(
        "/v1/forecast",
        json={
            "district_code": "29",
            "nature_family": "personal_injury",
            "jurisdiction_code": "3",
            "origin_code": "13",
        },
    ).json()
    forbidden = {".duckdb", ".ubj", ".onnx", ".joblib", ".pem", ".key"}
    public_forbidden = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in forbidden
        and not any(part in {".git", ".venv", "node_modules", "dist", "tmp"} for part in path.parts)
    ]
    checks = {
        "operations_ready": readiness.get("operations_analytics") == "ready",
        "duration_unavailable": readiness.get("duration_forecast") == "unavailable",
        "model_failed_not_promoted": provenance.get("model_status") == "failed_not_promoted",
        "forecast_refused": forecast.get("status") == "forecast_unavailable",
        "synthetic_cost_boundary": provenance.get("real_cost_forecast") is False,
        "demo_seed_deterministic": seed_replay,
        "full_population_reconciled": explorer.get("population", {}).get("statistical_records")
        == 5_008_334,
        "public_cube_matter_free": explorer.get("publication_policy", {}).get("matter_level_rows")
        == 0,
        "public_forbidden_artifacts": not public_forbidden,
    }
    return {
        "result": sum(checks.values()),
        "threshold": len(checks),
        "method": "Pinned API, provenance, refusal, deterministic-seed, full-population, and public-artifact replay.",
        "decision": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "forbidden_artifacts": public_forbidden,
        "limitation": "This local gate does not establish authenticated hosted operation or duration prediction readiness.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if result["decision"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
