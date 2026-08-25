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

## Planned browser query contract

DuckDB-WASM is an in-browser query engine, not a new HTTP API. M17 and M18 define three versioned
static contracts: a dataset manifest, a semantic metric registry, and worker messages.

The manifest identifies compatible schema and application versions, snapshot, partitions, counts,
sizes, and integrity metadata. The registry allowlists measures, dimensions, operators, formats,
support rules, and query templates. Worker requests carry a request identifier, registered query,
filter values, deterministic sort, projected columns, offset or cursor, and bounded limit. Worker
responses return Arrow data or typed progress, cancellation, compatibility, memory, network, and query
errors. Raw SQL from URL state or user input is not part of the public contract.
