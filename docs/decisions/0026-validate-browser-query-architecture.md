# Validate the browser query architecture

Status: implemented locally for M17. This decision authorizes contract-bound M16 and M18 work only.
It does not authorize data upload, deployment, push, publication, or public row-data activation.

## Decision

Use one Zstandard Parquet file per filing year, sorted by filing year, district, nature-of-suit family,
and opaque release key. Use 65,536-row groups as the provisional physical policy. Keep the existing
aggregate cube as the initial-view fast path and run bounded detail queries through DuckDB-WASM in its
asynchronous Web Worker.

Pin `@duckdb/duckdb-wasm` to `1.29.0`. Disable full HTTP-read fallback. Version 1.32.0 failed the local
registered HTTP Parquet path, while 1.29.0 passed it; upstream issue
[duckdb-wasm#2228](https://github.com/duckdb/duckdb-wasm/issues/2228) reports an HTTP-range regression
across versions 1.30.0 through 1.32.0. A later upgrade requires replaying this benchmark before merge.

Use GitHub Pages as the provisional row-data origin. Use content-versioned annual paths and accept the
currently observed 600-second Pages cache lifetime for the candidate. Keep `DATA_BASE_URL`
configurable so an approved object-storage origin can replace Pages without changing query semantics.
M22 must verify the exact public Parquet URLs, MIME type, CORS, byte ranges, redirects, cache behavior,
quota, cost, and rollback after fresh deployment approval.

## Evidence

The private 2019 representative partition contains 296,543 contract-valid statistical records in
6,312,722 bytes across five row groups. It preserves 21,788 collision-labeled records and 21,366
pending records, has 296,543 distinct opaque keys, and has zero prohibited findings.

The frozen measure, grouped-chart, 100-row page, and 200-row sort corpus passed in Chrome 151 on a
1440 by 900 desktop viewport and a 390 by 844 mobile viewport. Worst observed cold p95 was 27.7 ms and
worst warm p95 was 10.6 ms on loopback. The production aggregate shell LCP was 120 ms. The maximum
observed JavaScript heap was 17,197,661 bytes, with zero memory failures. Scan, grouping, sort, and
export queries were each terminated by replacing the worker, and every replacement recovered for a
bounded follow-up query.

Each desktop and mobile run produced 45 partial GETs and 12 partial HEAD probes, transferred 6,196,296
bytes across the complete corpus, and produced zero 200 full-file GETs. The local origin returned
Parquet MIME, CORS and Range headers, immutable cache headers, and HTTP 206. A read-only probe of the
existing Pages aggregate asset returned HTTPS, CORS `*`, `Accept-Ranges: bytes`, HTTP 206 for a
100-byte request, the correct JSON MIME, and `max-age=600`. Raw GitHub content and the release source
archive were rejected as data origins. The current release has no attached assets.

## Why

An annual partition keeps ordinary interactions to one temporal slice and fits the existing source
grain. The 64K row group creates five independently readable groups in a representative complete year
without producing excessive metadata. Sorting makes common district and case-family predicates useful
for row-group and column pruning. Worker replacement provides bounded cancellation even when a query
does not reach a cooperative interruption point.

Pages is already the shell origin, passed the safe public-file probe, has zero incremental cost for the
measured use, and its documented 1 GB site and soft 100 GB monthly bandwidth limits can contain the
projected artifact. These are operating bounds, not entitlements; M22 must revalidate them and may
select the object-storage fallback if the exact candidate fails.

## Alternatives rejected

- Permit DuckDB-WASM full HTTP fallback. Rejected because a range regression could silently download
  an entire partition during an ordinary interaction.
- Adopt DuckDB-WASM 1.32.0. Rejected because it failed the representative registered-URL path and its
  upstream range regression remains open.
- Put generated Parquet in Git history or serve it through `raw.githubusercontent.com`. Rejected
  because generated data belongs outside Git and the probe returned `text/plain` with a short cache.
- Use the GitHub release source archive as a data origin. Rejected because it redirected, ignored the
  Range request, and did not permit the requesting browser origin.
- Create an object-storage candidate during M17. Rejected because provider mutation and upload were not
  authorized.

## Changed

- Added a deterministic representative-partition builder that refuses public-repository output.
- Added a loopback-only, byte-range, CORS, immutable-cache Parquet origin with request accounting.
- Added the bounded DuckDB-WASM worker corpus and a local desktop/mobile evidence harness.
- Pinned DuckDB-WASM 1.29.0 and added the M17 production build target.
- Added focused tests for public-output refusal and byte-range origin behavior.
- Recorded the provisional annual partition, row-group, cache, and hosting policy.

## Limitations

- The mobile result is a responsive viewport on the same Chrome host, not physical low-memory hardware.
- `performance.memory` is observed JavaScript heap, not total browser-process or WebAssembly memory.
- Loopback-unthrottled timings establish architectural viability, not public internet performance.
- The representative year and query corpus do not replace M16 full-population reconciliation or M21
  reliability coverage.
- No exact public Parquet file exists yet, so Pages remains provisional until M22.

## Not done

- The full 5,008,334-row serving mart was not built.
- No semantic registry, report workspace, record explorer, or public download was implemented.
- No data or benchmark artifact was placed in Git.
- No upload, deployment, provider mutation, push, publication, or paid action occurred.
