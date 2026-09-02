# Security boundary

## Current aggregate release

The local release exposes only thresholded aggregate public-court metadata, historical cohort summaries,
synthetic scenarios, and explicit refusal responses. It never serves the private warehouse,
review packets, source archives, model artifacts, credentials, or matter-level records.

Controls include a 64 KiB request-body limit, a process-local 120 requests-per-minute client
limit, typed request validation, content-free structured audit logs, request identifiers,
browser hardening headers, approved HTTPS acquisition hosts, redirect revalidation, archive
expansion budgets, path containment, manifest SHA-256 verification, and artifact-bound review
promotion. Reviewer CSV exports neutralize spreadsheet formulas; Parquet is canonical.

The container runs as an unprivileged user and contains a deidentified aggregate SQLite seed plus
an identifier-free population cube. The cube uses the complete governed population for exact
national and marginal totals, with a minimum support of 200 for the smallest published cells.
It has no warehouse or cloud credentials and requires no live BigQuery connection.

Residual limits: the API is intended for a single local process. A multi-replica or internet
deployment requires authenticated access, a shared edge rate limit, TLS termination, centralized
logs, signed review approvals, and a fresh deployment-specific threat assessment.

The offline dbt environment currently inherits four `sqlparse` advisories. dbt-core 1.11.11 still
requires `sqlparse <0.6`, so no compatible patched release exists. The accepted exception is bounded:
`sqlparse` is excluded from the production requirements and container, processes only
repository-controlled SQL during local/CI analytics builds, and is re-audited when dbt changes its
constraint. Untrusted SQL must never enter that toolchain.

## Governed row-level release

The M15 publication contract permits only identifier-minimized statistical records in
generated data assets outside tracked Git. Public availability of the source does not authorize unrestricted
republishing. Direct and natural identifiers, names, text, review evidence, source paths, credentials,
and model artifacts remain prohibited. Opaque keys must be random or privately keyed and scoped to a
dataset version. Exact dates and office fields are excluded by the frozen linkability decision.

M17 validates the browser query engine against a local range-capable origin and uses read-only public
files to probe candidate-host HTTPS, CORS, redirects, range, cache, and content-type behavior. M22
verified those controls against every object at the approved production Worker; the manifest allowlists
every partition and compatible schema version. The upload-only route was removed after staging.
The application does not accept arbitrary remote paths or raw SQL. DuckDB-WASM runs in a Web Worker
with query cancellation, memory and result ceilings, projected columns, bounded paging, and typed
failure. Normal interactions cannot request all partitions implicitly.

CSV exports retain spreadsheet-formula neutralization and explicit row bounds. An unavailable or
unverified filtered-Parquet export is refused. The full immutable dataset download remains a separate,
explicit user action and is never an automatic fallback. M21 completed the physical security and
privacy review. M22 local preflight repeated row-value and packaged-text scans with zero findings;
live-origin checks pass for the exact production inventory. The Pages bundle pins the approved origin.
