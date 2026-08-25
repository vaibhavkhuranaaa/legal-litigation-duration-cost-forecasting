# Federal Civil Portfolio Intelligence

## Product contract

- Audience: legal-operations leaders and matter planners.
- Decision: monitor portfolio operations, compare observed historical cohorts, and test synthetic resource scenarios.
- Coverage: all federal districts, cases filed from 2010 through latest complete reporting period.
- Population: FJC IDB civil filings, pending cases, and terminations.
- Enrichment: CourtListener RECAP only after reviewed match and event-quality gates pass.
- Validation: U.S. Courts and AO aggregate tables.
- Model: Kaplan-Meier and XGBoost AFT remain failed evaluation evidence; duration forecast endpoints refuse.
- Current product: static aggregate dashboard plus a FastAPI and React TypeScript offline release.
- Next release: identifier-minimized Parquet serving mart, semantic metric registry, DuckDB-WASM
  query worker, synchronized report workspace, and bounded record explorer.
- Distribution: GitHub Pages and an aggregate offline container, with no warehouse credentials or
  live BigQuery queries.

## Boundaries

This product is planning analytics, not legal advice. It does not predict case outcomes, judge behavior, settlement, or real legal cost. Budget outputs use explicit synthetic assumptions only.

## Release policy

Failed model gates disable duration forecasts. Operations analytics and synthetic scenarios may ship with typed refusals, provenance, limitations, and no readiness claim for prediction. The current aggregate release is public. The planned row-level release remains unshipped until M15 through M22 pass and release approval is recorded.
