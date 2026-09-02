# Release security review

The deployed-release review covers the aggregate fast path and the v2.0 row release. The M15 section
freezes the row-level design boundary. M21 repeated the review against physical artifacts and local
runtime behavior. M22 rescanned the exact inventory and verified it through the approved production
Worker before Pages activation.

## M21 row-dashboard security result

The complete 5,008,334-row private candidate was scanned across physical schemas and values, its
manifest was scanned separately, and the built client was checked against the M15 allowlist and
denylist. The result is zero disallowed fields or values. The locked production browser dependency
graph reports zero known vulnerabilities.

The application now accepts only HTTPS or explicit loopback row origins and rejects credentials,
queries, fragments, redirects, unexpected media types, incompatible manifests, unexpected partition
paths, and responses that do not prove byte ranges and immutable caching. DuckDB-WASM disables full
HTTP fallback, registers only the selected annual partition, and runs under a 256 MB memory limit.

A diff-focused security review found one low-severity wildcard CORS issue in the local range reference
server. It was remediated before M21 closure with an exact repeated `--allow-origin` allowlist,
approved-origin reflection, `Vary: Origin`, and HTTP 403 for explicit unapproved origins. Runtime
verification confirms the hostile origin receives no access-control header while the approved origin
receives the expected 206 response.

M22 packages the allowlist-only generated dictionary, registry, manifest, application, and all 17
partitions into an exact 38-file candidate. Packaged text and all row values have zero credential or
private-path findings. No credentials, row assets, or private evidence entered tracked Git. The
production Worker exposes only allowlisted GET, HEAD, and OPTIONS paths from an immutable R2 prefix;
its temporary authenticated upload route was removed after staging. All live objects match the
manifest and CORS is exact-origin.

## M15 row-publication threat review

| Threat | M15 control | Residual limitation and next gate |
| --- | --- | --- |
| Direct identity disclosure | Deny source, natural, docket, PACER, RECAP, name, text, and review fields | M16 and M22 scanned every physical partition and value |
| Quasi-identifier linkage | Deny office and exact event dates; publish district and month only | Exact duration and public categories retain some linkability; M21 reviewed measured records and combinations |
| Opaque-key reversal or cross-release tracking | HMAC-SHA-256 with private 32-byte minimum secret, 128-bit output, and dataset-version scope | M16 proves full uniqueness; secret management remains private |
| Collision misrepresentation | Retain every collision record and require status and group count | No record may be called a canonical case unless source count is one |
| Null or censoring distortion | Pending is the logical inverse of event observed; termination month is null exactly when pending | M16 physical population and pending counts reconcile exactly |
| Schema or path substitution | Exact manifest and partition allowlists, version compatibility, row counts, bytes, and SHA-256 | M22 verifies the production remote origin before Pages activation |
| Credential or private-path leakage | Field denylist plus credential and local-path value patterns | M16, M21, and the M22 packaged candidate pass |
| Unbounded extraction | 10,000-row query limit, 50,000-row CSV limit, explicit Parquet and full-download actions | M20 implements formula-safe export and scoped provenance; M21 verifies transfer behavior |
| Source attribution or terms drift | Required FJC and CourtListener notices; public download remains approval-gated | M22 reverifies official terms before activation |
| Predictive misuse | Descriptive labels, collision grain, no model fields, no legal advice or outcome prediction | M21 reviewed product copy and exports |

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
