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

## Browser query contract

DuckDB-WASM is an in-browser query engine, not a new HTTP API. M15 through M20 now define the versioned
dataset manifest, `metrics.v1` semantic registry, bounded worker-query policy, URL-synchronized report
state, and governed row-query and export paths.

The manifest identifies compatible schema and application versions, snapshot, partitions, counts,
sizes, and integrity metadata. The registry allowlists measures, dimensions, operators, formats,
support rules, and query templates. It contains 11 measures, 17 compatible dimensions, and portfolio,
filing-cohort, and pending-inventory contexts. Worker requests carry a request identifier, registered query,
filter values, deterministic sort, projected columns, offset or cursor, and bounded limit. Worker
responses return Arrow data or typed progress, cancellation, compatibility, memory, network, and query
errors. Raw SQL from URL state or user input is not part of the public contract.

Record Explorer validates the complete manifest before activating any partition. It registers one
annual Parquet file for an interactive query, accepts only the 19 approved fields, parameterizes
district, nature-family, and opaque-key values, returns 200-row pages, and adds the opaque key as a
stable sort tie-breaker. CSV is capped at 50,000 rows and formula-safe. Filtered Parquet is capped at
10,000 rows and read back to verify its row count and projected schema. Successful bounded exports
also expose deterministic JSON provenance for the exact contract, scope, projection, and observed
row count. `VITE_ROW_DATA_BASE_URL` is
unset in the current public build, so these paths fail closed there. They are not HTTP service routes.

Filter values use bound parameters. Generated aggregate queries enforce context-specific support of at
least 200 records and cap results at 10,000 rows. See [semantic metrics](semantic-metrics.md).
