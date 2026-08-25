# Operations API

Version 1 exposes typed JSON contracts:

- `GET /v1/health`
- `GET /v1/readiness`
- `GET /v1/capabilities`
- `GET /v1/portfolio`
- `GET /v1/population-explorer`
- `POST /v1/benchmarks`
- `POST /v1/forecast`
- `GET /v1/milestones/availability`
- `POST /v1/scenarios`
- `GET /v1/provenance`

The population explorer returns a typed, versioned aggregate contract built from all 5,008,334 governed records. It exposes only supported counts, ratios, descriptive durations, dimensions, source snapshot, and publication rules; it contains no matter-level row or identifier.

Forecast requests always return `forecast_unavailable` because no M7 estimator passed every gate. The capability registry publishes machine-readable readiness and reason codes for operations analytics, individual duration forecasts, aggregate resolution forecasts, and synthetic scenarios. Benchmark responses are observed development-cohort summaries through March 31, 2024, not predictions. Scenario responses are synthetic and disclose all assumptions. Pydantic bounds reject malformed and unbounded requests with HTTP 422.
