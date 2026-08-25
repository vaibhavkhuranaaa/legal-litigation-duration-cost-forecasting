"""Emit deterministic reliability evidence for the local API boundary."""

from __future__ import annotations

import argparse
import json
import logging
from io import StringIO
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from litigation_planner.api import app
from litigation_planner.http_security import AdmissionControlMiddleware


def evaluate() -> dict[str, object]:
    client = TestClient(app)
    marker = "NEVER_LOG_THIS_PAYLOAD_89231"
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("litigation_planner.audit")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        oversized = client.post(
            "/v1/scenarios",
            content=(marker + "x" * 65_536),
            headers={"content-type": "application/json"},
        )
        forecast = {
            "district_code": "29",
            "nature_family": "personal_injury",
            "jurisdiction_code": "3",
            "origin_code": "13",
        }
        refusal_a = client.post("/v1/forecast", json=forecast)
        refusal_b = client.post("/v1/forecast", json=forecast)
    finally:
        logger.removeHandler(handler)

    limited = FastAPI()

    @limited.get("/")
    def ok() -> dict[str, bool]:
        return {"ok": True}

    limited.add_middleware(AdmissionControlMiddleware, requests_per_window=2)
    limited_client = TestClient(limited)
    statuses = [limited_client.get("/").status_code for _ in range(3)]
    logs = stream.getvalue()
    checks = {
        "oversized_request_rejected": oversized.status_code == 413,
        "rate_limit_enforced": statuses == [200, 200, 429],
        "forecast_refusal_deterministic": refusal_a.json() == refusal_b.json(),
        "forecast_refusal_active": refusal_a.json().get("status") == "forecast_unavailable",
        "audit_log_excludes_payload": marker not in logs,
        "security_headers_present": oversized.headers.get("x-content-type-options") == "nosniff",
    }
    return {
        "result": sum(checks.values()),
        "threshold": len(checks),
        "method": "FastAPI boundary replay with request-size, rate, refusal, log-content, and header probes.",
        "decision": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "limitation": "Rate limiting is process-local; a reverse proxy must enforce a shared limit if replicas are added.",
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
