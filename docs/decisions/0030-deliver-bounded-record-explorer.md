# Deliver a bounded browser record explorer

Status: implemented locally for M20. This decision authorizes no M21 hardening, data upload,
deployment, push, publication, or provider mutation.

## Decision

Use the existing DuckDB-WASM runtime to query one manifest-approved annual Parquet partition at a
time. Keep the aggregate cube as the initial scope summary. Compile every row query from an allowlist
of the 19 approved public fields, parameterize filter values, project selected columns, enforce a
200-row interactive page and 10,000-row query ceiling, and add the opaque record key as the stable
sort tie-breaker.

Render at most 19 data rows in the DOM through native table windowing. Keep one projected column
pinned, expose native column selection and width controls, and load the full approved detail for one
opaque key through a separate bounded lookup.

CSV export replays the active annual partition, filters, sort, and projection with a 50,000-row
ceiling. Values with spreadsheet formula prefixes receive a leading apostrophe before CSV quoting.
Filtered Parquet replays the same scope with a 10,000-row ceiling, then reads the output back through
DuckDB to verify row count and projected schema before the browser receives a Blob. Any write or
verification failure returns a refusal and no download.

Each successful bounded export also prepares a deterministic JSON provenance sidecar as a separate,
explicit download. The sidecar records the public contract, dataset, schema, metric registry, source
cutoff and attribution, active filters and sort, projected columns, row ceiling, format, and observed
exported row count. It omits a generated timestamp so identical export scopes produce identical
metadata.

The complete-data path is separate from interactive queries. It requires an explicit terms
acknowledgement before showing the immutable manifest and 17 annual partition links. The path exists
only when an approved row origin is configured. M20 verification uses the private loopback origin;
the current public build remains aggregate-only.

## Why

- One annual partition prevents ordinary exploration from reading the complete dataset.
- Reusing DuckDB-WASM and browser primitives avoids another table or export dependency.
- Parameterized allowlisted SQL keeps URL and interface values outside query structure.
- A stable opaque-key tie-breaker prevents page-boundary duplication or drift.
- Read-back verification makes filtered Parquet a checked artifact rather than a best-effort file.
- Separate complete-data links make the high-transfer action visible and deliberate.

## Alternatives rejected

- Render all 200 rows at once. Rejected because browser work should remain bounded independently of
  query size.
- Query all 17 partitions for every interaction. Rejected because it violates the ordinary-transfer
  boundary.
- Add a third-party data-grid package. Rejected because native table semantics, CSS sticky columns,
  a range input, and a small row window satisfy the frozen requirement.
- Export CSV directly from visible DOM rows. Rejected because virtualized rows are not the complete
  bounded result and would not preserve declared query scope.
- Trust Parquet writer completion. Rejected because row and schema mismatches must fail closed.
- Bundle row assets into tracked Git for convenience. Rejected because M16 data and manifests remain
  private until M22 receives fresh approval.

## Evidence

- A 2025 New Jersey civil-rights query returns exactly 1,710 records in both the browser and a direct
  private DuckDB reconciliation.
- The first five rows at offsets 0 and 200 match direct DuckDB results under elapsed-days descending
  and opaque-key ascending order.
- CSV and read-back-verified Parquet each export 1,710 rows and eight projected columns in the frozen
  scenario, with an explicit provenance sidecar available after success.
- Twelve focused frontend tests pass, including unregistered-field refusal, deterministic provenance,
  and six formula-prefix
  fixtures with zero unsafe findings.
- The virtualized table renders at most 19 data rows on desktop and mobile while holding 200 rows in
  the current result page.
- All 21 observed Parquet responses are HTTP 206, target only the 2025 partition, and include zero
  unintended HTTP 200 full-file responses.

## Changed

- Added the allowlisted row-query, deterministic-sort, CSV, and value-normalization module.
- Extended the browser engine with manifest validation, annual partition activation, page and count
  queries, key detail, bounded CSV, and read-back-verified Parquet.
- Replaced the M19 Record Explorer refusal with the virtualized table, controls, detail panel,
  exports, explicit complete-data path, and typed unavailable, loading, empty, error, and refusal
  states.
- Added focused tests and updated interface, architecture, API, release-plan, and frontend guidance.

## Not done

- No M21 reliability, accessibility, browser-compatibility, memory, cache, or security gate was
  claimed.
- No row asset entered tracked Git.
- No data was uploaded, deployed, pushed, or published.
