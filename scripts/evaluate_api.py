"""Capture typed API and refusal evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from litigation_planner.api import app


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    client = TestClient(app)
    forecast = client.post(
        "/v1/forecast",
        json={
            "district_code": "29",
            "nature_family": "tort_personal_injury",
            "jurisdiction_code": "4",
            "origin_code": "13",
        },
    )
    invalid = client.post("/v1/scenarios", json={})
    readiness = client.get("/v1/readiness")
    versioned_paths = sorted(path for path in app.openapi()["paths"] if path.startswith("/v1/"))
    report = {
        "versioned_paths": versioned_paths,
        "versioned_path_count": len(versioned_paths),
        "forecast_refusal_status": forecast.json()["status"],
        "invalid_input_http_status": invalid.status_code,
        "operations_readiness": readiness.json()["operations_analytics"],
        "forecast_readiness": readiness.json()["duration_forecast"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
