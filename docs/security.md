# Security boundary

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
