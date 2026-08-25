"""Typed local API for the non-predictive operations release."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from litigation_planner.demo import (
    COHORTS,
    PORTFOLIO,
    RELEASE_SCHEMA_VERSION,
    read_cohort,
    read_portfolio,
)
from litigation_planner.http_security import AdmissionControlMiddleware
from litigation_planner.milestones import assess_milestone_availability
from litigation_planner.scenarios import ScenarioAssumptions, build_scenario

RELEASE_VERSION = RELEASE_SCHEMA_VERSION
SOURCE_CUTOFF = "2026-03-31"
DEVELOPMENT_CUTOFF = "2024-03-31"
DEMO_DB_PATH = os.environ.get("DEMO_DB_PATH")
POPULATION_CUBE_PATH = os.environ.get(
    "POPULATION_CUBE_PATH",
    str(Path(__file__).resolve().parents[2] / "frontend/src/full-population.v1.json"),
)
INDIVIDUAL_FAILURES = (
    "baseline.calibration_730d.failed",
    "baseline.supported_slice_calibration.failed",
    "challenger.calibration_730d.failed",
    "challenger.supported_slice_calibration.failed",
    "policy.baseline_required",
)
PORTFOLIO_FAILURES = (
    "development.all_folds_failed",
    "final_holdout.sealed",
)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    release_version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    operations_analytics: Literal["ready"]
    duration_forecast: Literal["unavailable"]
    milestone_events: Literal["unavailable"]
    scenario_engine: Literal["ready"]
    reason: str


class PortfolioResponse(BaseModel):
    source_snapshot: str
    statistical_records: int
    pending_records: int
    pending_share: float
    collision_free_cases: int
    promoted_recap_matches: int
    recap_match_coverage: float
    interpretation: str


class BenchmarkRequest(BaseModel):
    cohort: Literal[
        "ordinary_original",
        "multidistrict_litigation",
        "other_procedural_origin",
        "social_security_review",
    ]


class BenchmarkResponse(BaseModel):
    status: Literal["observed_benchmark"]
    cohort: str
    cases: int
    termination_365_day_share: float
    termination_730_day_share: float
    snapshot_censored_share: float
    outcomes_through: str
    limitation: str


class DistrictDimension(BaseModel):
    district_code: str
    court_id: str
    ao_label: str


class PopulationSummary(BaseModel):
    statistical_records: int
    pending_records: int
    collision_free_records: int
    matched_records: int


class PublishedCellCounts(BaseModel):
    available: int
    published: int


class PublicationPolicy(BaseModel):
    full_population_used: Literal[True]
    matter_level_rows: Literal[0]
    minimum_support: int
    smallest_grain_cells: dict[str, PublishedCellCounts]
    limitation: str


class ExplorerDimensions(BaseModel):
    districts: list[DistrictDimension]
    nature_families: list[str]
    filing_years: list[int]
    age_bands: list[str]


class PortfolioSlice(BaseModel):
    district_code: str | None
    nature_family: str | None
    total_records: int
    collision_free_records: int
    pending_records: int
    terminated_records: int
    matched_records: int
    supported_nature_records: int
    pending_share: float
    match_coverage: float
    duration_support_count: int | None
    observed_terminations: int | None
    censored_records: int | None
    average_observed_duration_days: float | None


class FilingPoint(BaseModel):
    filing_year: int
    district_code: str | None
    nature_family: str | None
    cohort_records: int
    observed_terminations: int
    pending_records: int
    matched_records: int
    followup_days: int


class PendingAgePoint(BaseModel):
    age_band: str
    district_code: str | None
    nature_family: str | None
    pending_records: int
    matched_pending_records: int
    average_age_days: float


class PopulationExplorerResponse(BaseModel):
    schema_version: Literal["1"]
    source_snapshot: str
    population: PopulationSummary
    publication_policy: PublicationPolicy
    dimensions: ExplorerDimensions
    portfolio_slices: list[PortfolioSlice]
    filing_series: list[FilingPoint]
    pending_age_series: list[PendingAgePoint]


class ForecastRequest(BaseModel):
    district_code: str = Field(min_length=2, max_length=2, pattern=r"^[0-9A-Z-]{2}$")
    nature_family: str = Field(min_length=1, max_length=80)
    jurisdiction_code: str = Field(min_length=1, max_length=2)
    origin_code: str = Field(min_length=1, max_length=2)


class ForecastRefusal(BaseModel):
    status: Literal["forecast_unavailable"]
    reason: str
    reason_codes: list[str]
    failed_gates: dict[str, float]
    safe_alternatives: list[str]
    limitation: str


class MilestoneResponse(BaseModel):
    status: Literal["event_unavailable"]
    event_updates_enabled: bool
    match_coverage: float
    missing_event_fields: list[str]
    fallback: str
    limitation: str


class ScenarioRequest(BaseModel):
    matters: int = Field(ge=1, le=10_000)
    horizon_months: int = Field(ge=1, le=60)
    attorney_hours_per_matter_month: float = Field(ge=0, le=500)
    paralegal_hours_per_matter_month: float = Field(ge=0, le=500)
    attorney_rate_usd: float = Field(ge=0, le=5_000)
    paralegal_rate_usd: float = Field(ge=0, le=5_000)
    productive_hours_per_fte_month: float = Field(default=120, gt=0, le=744)
    low_multiplier: float = Field(default=0.8, ge=0.1, le=1)
    high_multiplier: float = Field(default=1.25, ge=1, le=5)


class ScenarioCase(BaseModel):
    name: str
    multiplier: float
    attorney_hours: float
    paralegal_hours: float
    attorney_fte: float
    paralegal_fte: float
    budget_usd: float


class ScenarioResponse(BaseModel):
    scenario_type: Literal["synthetic"]
    observed_cost_data_used: Literal[False]
    assumptions: dict[str, int | float]
    cases: list[ScenarioCase]
    limitation: str


class ProvenanceResponse(BaseModel):
    release_version: str
    fjc_snapshot: str
    recap_snapshot: str
    development_outcomes_end: str
    model_status: Literal["failed_not_promoted"]
    legal_advice: Literal[False]
    real_cost_forecast: Literal[False]


app = FastAPI(
    title="Federal Civil Litigation Operations Planner",
    version="1.1.0",
)
app.add_middleware(AdmissionControlMiddleware)


@app.get("/health", response_model=HealthResponse)
@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", release_version=RELEASE_VERSION)


@app.get("/readiness", response_model=ReadinessResponse)
@app.get("/v1/readiness", response_model=ReadinessResponse)
def readiness() -> ReadinessResponse:
    return ReadinessResponse(
        status="ready",
        operations_analytics="ready",
        duration_forecast="unavailable",
        milestone_events="unavailable",
        scenario_engine="ready",
        reason="M7 model gates failed; operations analytics and synthetic scenarios remain available.",
    )


@app.get("/v1/capabilities")
def capabilities() -> dict[str, object]:
    return {
        "release_mode": "descriptive_only",
        "capabilities": [
            {
                "capability_id": "operations_analytics",
                "status": "ready",
                "reason_codes": [],
            },
            {
                "capability_id": "individual_duration_forecast",
                "status": "blocked",
                "reason_codes": list(INDIVIDUAL_FAILURES),
            },
            {
                "capability_id": "portfolio_12m_resolution",
                "status": "blocked",
                "reason_codes": list(PORTFOLIO_FAILURES),
            },
            {
                "capability_id": "synthetic_scenarios",
                "status": "ready",
                "reason_codes": [],
            },
        ],
    }


@app.get("/v1/portfolio", response_model=PortfolioResponse)
def portfolio() -> PortfolioResponse:
    source_snapshot, total, pending, collision_free, matches = (
        read_portfolio(Path(DEMO_DB_PATH)) if DEMO_DB_PATH else PORTFOLIO
    )
    return PortfolioResponse(
        source_snapshot=source_snapshot,
        statistical_records=total,
        pending_records=pending,
        pending_share=pending / total,
        collision_free_cases=collision_free,
        promoted_recap_matches=matches,
        recap_match_coverage=matches / collision_free,
        interpretation="Observed nationwide public court metadata; not a duration forecast.",
    )


@lru_cache(maxsize=1)
def _population_explorer() -> PopulationExplorerResponse:
    return PopulationExplorerResponse.model_validate_json(Path(POPULATION_CUBE_PATH).read_text())


@app.get("/v1/population-explorer", response_model=PopulationExplorerResponse)
def population_explorer() -> PopulationExplorerResponse:
    return _population_explorer()


@app.post("/v1/benchmarks", response_model=BenchmarkResponse)
def benchmark(request: BenchmarkRequest) -> BenchmarkResponse:
    cases, rate_365, rate_730, censored = (
        read_cohort(Path(DEMO_DB_PATH), request.cohort) if DEMO_DB_PATH else COHORTS[request.cohort]
    )
    return BenchmarkResponse(
        status="observed_benchmark",
        cohort=request.cohort,
        cases=cases,
        termination_365_day_share=rate_365,
        termination_730_day_share=rate_730,
        snapshot_censored_share=censored,
        outcomes_through=DEVELOPMENT_CUTOFF,
        limitation="Historical cohort average; not a matter-specific prediction or legal advice.",
    )


@app.post("/v1/forecast", response_model=ForecastRefusal)
def forecast_refusal(_: ForecastRequest) -> ForecastRefusal:
    return ForecastRefusal(
        status="forecast_unavailable",
        reason="No estimator passed all M7 calibration and supported-slice gates.",
        reason_codes=list(INDIVIDUAL_FAILURES),
        failed_gates={
            "kaplan_meier_24m_error": 0.1147201731801033,
            "kaplan_meier_max_slice_error": 0.7781025598530199,
            "xgboost_24m_error": 0.08093826472759247,
            "xgboost_max_slice_error": 0.525208009291115,
        },
        safe_alternatives=["portfolio_summary", "observed_cohort_benchmark", "synthetic_scenario"],
        limitation="Public metadata cannot support an individual duration forecast at required gates.",
    )


@app.get("/v1/milestones/availability", response_model=MilestoneResponse)
def milestone_availability() -> MilestoneResponse:
    result = assess_milestone_availability(
        {"id", "date_filed", "date_terminated", "docket_number"},
        2_065_537,
        4_645_719,
    )
    return MilestoneResponse(
        status="event_unavailable",
        event_updates_enabled=result.event_updates_enabled,
        match_coverage=result.match_coverage,
        missing_event_fields=list(result.missing_event_fields),
        fallback=result.fallback,
        limitation=result.limitation,
    )


@app.post("/v1/scenarios", response_model=ScenarioResponse)
def scenario(request: ScenarioRequest) -> ScenarioResponse:
    result = build_scenario(ScenarioAssumptions(**request.model_dump()))
    return ScenarioResponse.model_validate(result)


@app.get("/v1/provenance", response_model=ProvenanceResponse)
def provenance() -> ProvenanceResponse:
    return ProvenanceResponse(
        release_version=RELEASE_VERSION,
        fjc_snapshot=SOURCE_CUTOFF,
        recap_snapshot="2026-06-30",
        development_outcomes_end=DEVELOPMENT_CUTOFF,
        model_status="failed_not_promoted",
        legal_advice=False,
        real_cost_forecast=False,
    )


static_dir = os.environ.get("STATIC_DIR")
if static_dir and Path(static_dir).is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
