import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from litigation_planner.api import INDIVIDUAL_FAILURES, app
from litigation_planner.http_security import AdmissionControlMiddleware

client = TestClient(app)


def test_readiness_splits_operations_from_forecast() -> None:
    response = client.get("/v1/readiness")

    assert response.status_code == 200
    assert response.json()["operations_analytics"] == "ready"
    assert response.json()["duration_forecast"] == "unavailable"


def test_forecast_returns_typed_refusal() -> None:
    response = client.post(
        "/v1/forecast",
        json={
            "district_code": "29",
            "nature_family": "tort_personal_injury",
            "jurisdiction_code": "4",
            "origin_code": "13",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "forecast_unavailable"
    assert response.json()["reason_codes"] == list(INDIVIDUAL_FAILURES)
    assert response.json()["failed_gates"]["kaplan_meier_max_slice_error"] > 0.10


def test_capability_registry_matches_release_evidence() -> None:
    response = client.get("/v1/capabilities")
    evidence = json.loads(Path("evaluation/m7-release-decision.json").read_text())
    capabilities = {item["capability_id"]: item for item in response.json()["capabilities"]}

    assert response.status_code == 200
    assert response.json()["release_mode"] == "descriptive_only"
    assert capabilities["operations_analytics"]["status"] == "ready"
    assert capabilities["individual_duration_forecast"]["status"] == "blocked"
    assert (
        capabilities["individual_duration_forecast"]["reason_codes"]
        == evidence["capabilities"]["individual_duration_forecast"]["reason_codes"]
    )


def test_benchmark_is_observed_not_predictive() -> None:
    response = client.post("/v1/benchmarks", json={"cohort": "social_security_review"})

    assert response.status_code == 200
    assert response.json()["status"] == "observed_benchmark"
    assert "not a matter-specific prediction" in response.json()["limitation"]


def test_scenario_contract_is_synthetic() -> None:
    response = client.post(
        "/v1/scenarios",
        json={
            "matters": 10,
            "horizon_months": 6,
            "attorney_hours_per_matter_month": 5,
            "paralegal_hours_per_matter_month": 8,
            "attorney_rate_usd": 300,
            "paralegal_rate_usd": 125,
        },
    )

    assert response.status_code == 200
    assert response.json()["scenario_type"] == "synthetic"
    assert response.json()["observed_cost_data_used"] is False


def test_validation_bounds_bad_scenario() -> None:
    response = client.post("/v1/scenarios", json={})

    assert response.status_code == 422


def test_admission_control_rejects_oversized_body() -> None:
    response = client.post(
        "/v1/forecast",
        content=b"{" + b'"padding":"' + b"x" * 70_000 + b'"}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "request body exceeds limit"


def test_admission_control_rate_limits_per_client() -> None:
    limited = FastAPI()
    limited.add_middleware(AdmissionControlMiddleware, requests_per_window=2, window_seconds=60)

    @limited.get("/")
    def ok() -> dict[str, str]:
        return {"status": "ok"}

    limited_client = TestClient(limited)
    assert limited_client.get("/").status_code == 200
    assert limited_client.get("/").status_code == 200
    assert limited_client.get("/").status_code == 429


def test_api_security_headers_are_present() -> None:
    response = client.get("/v1/readiness")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]
