# Verify the inactive row candidate and hold publication

Status: M22 verification complete on 2026-09-01. Final publication is held.

Live status is superseded by [decision 0034](0034-publish-row-analytics-release.md). This record remains
the historical candidate-verification decision.

## Decision

Accept the approved inactive Cloudflare candidate as verified M22 evidence. Keep the current v1.1
aggregate GitHub Pages release active. Do not activate the candidate for production, change Pages,
push, or publish without a new explicit approval.

The verified candidate is the exact 38-file, 185,756,777-byte inventory with a privately recorded
frozen digest, stored under one immutable private R2 prefix and served by the inactive read-only Worker at
`https://legal-litigation-row-candidate.gp-access-planner.workers.dev`.

## Why

The inactive target permits exact live verification and rollback without replacing the supported
aggregate dashboard. Keeping the frozen digest in the private delivery record avoids turning a public
decision note into an inventory locator.

## Alternatives rejected

- Activating the candidate as production was rejected because final publication was not authorized.
- Reusing the current Pages production route was rejected because it has no inactive verification slot
  for the generated mart.

## Evidence

- All 38 live objects and 185,756,777 bytes match the frozen local manifest; SHA-256 mismatches and
  redirects are zero.
- HTTPS, exact-origin CORS, Parquet MIME, immutable cache, and byte-range behavior pass. The temporary
  authenticated upload route was removed after staging.
- Browser verification loads 313,960 matching 2025 records, returns bounded 200-row pages, opens an
  approved-field detail record, recovers from cancellation, has zero mobile overflow, and records a
  ten-query p95 of 2,256 ms against the 3,000 ms gate.
- Provider rollback to the prior read-only Worker version and restoration of the verified version pass
  for both the HTML shell and Parquet range request.
- Measured storage and request volume remain within current Cloudflare free allowances. Reconciled
  incremental cost is $0; no paid overage is enabled or authorized.
- All 25 local and eight deployment checks pass, for 33 of 33 frozen M22 checks.

## Not done

This decision records verification, not publication. It changes no GitHub Pages workflow or public
production route, pushes no Git state, and publishes no release. The inactive candidate may remain
reachable for verification, but it is not the supported production product.

## Changed

- M22 moved from local preflight to verified inactive-candidate evidence: all 33 frozen checks passed.
- The production route, Pages workflow, publication gate, and supported product remain unchanged.
