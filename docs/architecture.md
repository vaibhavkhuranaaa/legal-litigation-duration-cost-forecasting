# Architecture

## Local release path

The release container serves a compiled React client and versioned FastAPI contracts from one
unprivileged process. Portfolio and cohort endpoints read a deidentified, aggregate-only SQLite seed
in read-only mode. The scenario endpoint is a pure deterministic calculation. Forecast and
milestone-event paths terminate in typed refusal or unavailability responses. No release request can
reach the private DuckDB warehouse, source archives, review packets, cloud services, or a model.

## Decision flow

```mermaid
flowchart LR
  F["FJC IDB civil population"] --> R["Immutable raw manifests"]
  C["CourtListener RECAP candidates"] --> M["Reviewed matching gate"]
  A["U.S. Courts and AO aggregates"] --> V["Reconciliation"]
  R --> L["Private local Parquet raw"]
  L --> Q["Local dbt contract gate"]
  Q --> D["Statistical records, collision-free cases, exceptions"]
  L -. "approval-gated load" .-> W["GCS and BigQuery raw"]
  M --> W
  W -. "future approved build" .-> D
  D --> V
  D --> T["Governed analytics marts"]
  M --> T
  T --> K["Kaplan-Meier baseline"]
  D --> X["XGBoost AFT challenger"]
  K --> P["Champion policy and abstention"]
  X --> P
  P --> S["Seeded deidentified SQLite"]
  S --> API["FastAPI"]
  API --> UI["React operations and planner workspaces"]
  Y["Synthetic scenario assumptions"] --> API
```

## Data boundary

FJC defines population. Pending cases remain pending with an explicit censoring date. CourtListener data enriches only reviewed matches. AO tables validate aggregates but never substitute for case-level data. Raw identifiers remain private. Seeded demo uses stable opaque identifiers and no live warehouse access.

M3 verifies the local raw boundary over the complete FJC archive. It selects approved metadata fields before text decoding, excludes party and judge fields, requires strict UTF-8 for selected values, partitions 2010 onward rows by filing year, and quarantines structural failures. Accepted, pre-window excluded, and quarantined counts must equal all source rows.

M4 runs dbt Core against the private Parquet source through a private DuckDB development target. Staging preserves raw and provenance fields. Intermediate models derive event observation, right censoring, duration, exact nature-of-suit mappings, and natural-key collision status. Marts separate all statistical records from collision-free case records and identity exceptions. Contracts, source freshness, relationships, reconciliation tests, and an expected contract failure gate run locally and in CI. The DuckDB target is development evidence only. BigQuery execution, cloud lineage, and deployed partition behavior remain unverified.

M5 stages only reviewed one-to-one FJC and RECAP matches. M6 builds portfolio, filing-cohort, pending-inventory, duration-summary, comparable-case, and data-coverage marts. Aggregate views retain the complete statistical population. Record-level comparables retain only collision-free cases. RECAP identity contributes availability flags and provenance, not duration truth. Two dbt exposures define portfolio and future modeling consumers.

M7 evaluates Kaplan-Meier and XGBoost AFT locally against the private comparable-case mart. A versioned contract fixes intake-known features, calendar splits, support rules, evaluation horizons, bootstrap comparison, and shipping gates. Both estimators fail required calibration, so the architecture stops at descriptive marts and does not expose a scoring path. Private evaluation and model files are retained only as negative evidence.

## Delivery boundary

Local checks and source-controlled contracts are authorized. Private generated dbt documentation and the local warehouse remain outside Git. Existing cloud state is not assumed accurate. Any reconciliation is read-only and separately documented. Provisioning, deployment, spend, public exposure, push, publication, and portfolio work require owner approval.

## Failure policy

Schema failures quarantine data. Match ambiguity blocks enrichment. Failed baseline limits product to descriptive analytics. Failed challenger retains Kaplan-Meier. Missing or incompatible model artifacts fail readiness. Sparse cohorts receive abstention, never a forced estimate.
