# Architecture

## Current verified release path

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
  P -- "all gates pass only" --> G["Promoted scoring artifact"]
  P -- "current failed state" --> F["Typed forecast refusal"]
  T --> S["Seeded deidentified SQLite"]
  T --> E["Deterministic aggregate cube"]
  S --> API["FastAPI"]
  G --> API
  F --> API
  E --> API
  E --> UI["React portfolio intelligence dashboard"]
  API --> UI
  Y["Synthetic scenario assumptions"] --> API
```

## Analytics interface architecture

The interface uses one global portfolio scope instead of independent report filters. Report, district,
case family, historical-cohort context, ranking mode, and drill origin are reflected in a canonical URL.
Pure TypeScript selectors derive the selected portfolio slice, annual filing series, pending-age series,
district ranking, case-family ranking, and latest complete-year change from the versioned cube. Relative
URL bookmarks in browser local storage restore the same compatible report context.

`App.tsx` owns cancellable data loading, URL history, retry, and state normalization.
`ReportWorkspace.tsx` owns the eight-report shell, shared scope, navigation, bookmarks, and report
composition. `RecordExplorer.tsx` owns the bounded table, column controls, detail, and download
workflow. `record-explorer.ts` owns allowlisted query compilation, stable sorting, CSV safety, and
normalization. `row-query-engine.ts` validates the manifest and executes one annual partition through
DuckDB-WASM. `row-origin-contract.ts` rejects incompatible origins, manifests, redirects, media types,
and non-range partition responses before query registration. Cancellation and timeout replace the
worker while preserving selected scope. `report-state.ts` owns pure URL parsing and serialization;
`AnalyticsDashboard.tsx`
retains shared chart renderers; and `population.ts` retains deterministic selectors.
The FastAPI service remains the typed runtime boundary, while the static Pages build loads the identical
cube directly. Neither path can access private data.

The synthetic scenario engine is a connected secondary workspace rather than the product's primary claim. It accepts bounded user assumptions and returns deterministic sensitivity cases. It does not consume the selected portfolio as an implied forecast, observed cost, or recommended staffing plan.

## Governed M15 through M22 path

The v2.0 release adds a separate browser serving engine. A deterministic private build produces an
identifier-minimized statistical-record mart, annual Zstandard Parquet partitions, and an immutable
manifest. The declarative semantic metric registry remains tracked and tested; its compiled copy is a
generated deployment asset. Parquet, manifests containing data paths, and other generated data assets
do not enter tracked Git. GitHub Pages serves the application shell; an approved immutable R2 prefix
and read-only Worker serve the generated row assets without placing them in Git history. The Pages
workflow injects the production row-data origin at build time.

The React shell loads the aggregate cube first and uses it for all eight report destinations. M20
runs detail queries in DuckDB-WASM inside its browser worker and returns bounded Arrow pages to a
virtualized table. It activates one annual partition, projects approved columns, parameterizes filter
values, applies a stable opaque-key tie-breaker, and enforces result ceilings. CSV and filtered
Parquet repeat the declared scope; Parquet is read back for row and schema verification, and each
bounded export prepares a deterministic JSON provenance sidecar. Complete-data
links remain a separate explicit path.

This browser DuckDB-WASM engine is distinct from the private DuckDB development warehouse. It can
access only the published mart. The app reads all paths through `DATA_BASE_URL`; an object-storage
fallback may replace the Pages origin only if M17 evidence requires it and the release contract stays
identical. A versioned manifest activates the application and data together, and rollback restores the
last verified manifest plus application bundle.

The approved M22 run uploaded one immutable object-store prefix and verified its exact Parquet URLs
through the production Worker before Pages activation. The aggregate cube remains the initial-render
fast path and fail-closed fallback.

```mermaid
flowchart LR
  H["Private statistical-record mart"] --> B["Public mart builder"]
  B --> G["Privacy, contract, and reconciliation gates"]
  G --> P["Annual Parquet partitions"]
  T["Tracked metric registry"] --> G
  G --> M["Manifest and compiled registry"]
  G --> C["Aggregate cube"]
  P --> O["Versioned static data origin"]
  M --> O
  C --> U["React report shell"]
  O --> W["DuckDB-WASM Web Worker"]
  W --> A["Bounded Arrow batches"]
  A --> U
```

The complete plan and performance gates are in
[row-level analytics release plan](row-level-analytics-plan.md).

## Data boundary

FJC defines population. Pending cases remain pending with an explicit censoring date. CourtListener data enriches only reviewed matches. AO tables validate aggregates but never substitute for case-level data. Raw identifiers remain private. Seeded demo uses stable opaque identifiers and no live warehouse access.

M3 verifies the local raw boundary over the complete FJC archive. It selects approved metadata fields before text decoding, excludes party and judge fields, requires strict UTF-8 for selected values, partitions 2010 onward rows by filing year, and quarantines structural failures. Accepted, pre-window excluded, and quarantined counts must equal all source rows.

M4 runs dbt Core against the private Parquet source through a private DuckDB development target. Staging preserves raw and provenance fields. Intermediate models derive event observation, right censoring, duration, exact nature-of-suit mappings, and natural-key collision status. Marts separate all statistical records from collision-free case records and identity exceptions. Contracts, source freshness, relationships, reconciliation tests, and an expected contract failure gate run locally and in CI. The DuckDB target is development evidence only. BigQuery execution, cloud lineage, and deployed partition behavior remain unverified.

M5 stages only reviewed one-to-one FJC and RECAP matches. M6 builds portfolio, filing-cohort, pending-inventory, duration-summary, comparable-case, and data-coverage marts. Aggregate views retain the complete statistical population. Record-level comparables retain only collision-free cases. RECAP identity contributes availability flags and provenance, not duration truth. Two dbt exposures define portfolio and future modeling consumers.

M7 evaluates Kaplan-Meier and XGBoost AFT locally against the private comparable-case mart. A versioned contract fixes intake-known features, calendar splits, support rules, evaluation horizons, bootstrap comparison, and shipping gates. Both estimators fail required calibration, so the architecture stops at descriptive marts and does not expose a scoring path. Private evaluation and model files are retained only as negative evidence.

## Delivery boundary

Local checks and source-controlled contracts are authorized. Private generated dbt documentation and the local warehouse remain outside Git. Existing cloud state is not assumed accurate. Any reconciliation is read-only and separately documented. New cloud provisioning, spend, deployment targets, and repository write actions require explicit owner approval; the current static dashboard and tagged release were published through those gates.

## Failure policy

Schema failures quarantine data. Match ambiguity blocks enrichment. Failed baseline limits product to descriptive analytics. Failed challenger retains Kaplan-Meier. Missing or incompatible model artifacts fail readiness. Sparse cohorts receive abstention, never a forced estimate.
