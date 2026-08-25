# Release security review

This review covers the current aggregate v1.1 release only. It does not authorize the planned
row-level serving mart. M21 requires a new review of the M15 field contract, linkability decisions,
opaque-key generation, manifest and partition allowlisting, remote range behavior, worker isolation,
query and memory bounds, caching, export, dependency posture, and rollback before M22 can publish.

The release boundary was reviewed across API admission, archive ingestion, source provenance,
human-review promotion, spreadsheet export, public artifacts, browser rendering, secrets, runtime
dependencies, and container contents. Validated issues were remediated with bounded requests and
archives, approved HTTPS destinations and redirect checks, SHA-256 binding, path containment,
formula neutralization, content-free audit logs, browser headers, and public-output guards.

The production dependency set contains 14 pinned API packages and excludes dbt, cloud clients,
scientific libraries, and `sqlparse`. The frontend audit reports zero known vulnerabilities. The
container runs as uid/gid 999, ships only the API modules, built static assets, and aggregate SQLite
seed, and has no credential configuration.

The offline dbt toolchain currently resolves `sqlparse` 0.5.5 because dbt 1.9 requires a version
below 0.6; four 2026 advisories have a 0.6.0 fix. This parser is not present in the release image,
is not reachable through the API, and receives only repository-controlled SQL. Upgrade dbt when a
compatible release is available. Internet deployment still requires the controls listed in
[security.md](security.md).
