# Hold the row release at a private candidate

Status: local preflight decision for M22. The milestone and public release remain pending. This
decision authorizes no upload, deployment, provider mutation, push, publication, or live-site change.

Live status is superseded by [decision 0033](0033-verify-inactive-row-candidate.md). This record remains
the immutable local-preflight decision.

## Decision

Retain release version 2.0.0 as an immutable private candidate until an exact inactive deployment
target is approved and passes the live contract. The candidate packages the Pages application,
aggregate cube, compiled `metrics.v1` registry, generated allowlist-only data dictionary, governed
manifest, and all 17 annual Parquet partitions. Every file is covered by `release-manifest.json`.

Do not adapt the current Pages workflow during local preflight. It builds only tracked frontend files,
deploys directly to the production Pages environment, and has no approved mechanism to inject the
private generated mart into an inactive candidate. The observed Pages cache policy also does not prove
the immutable partition caching required by the client. Select or alter a host only after the owner
approves the exact target and provider mutation.

## Why

- Keeping generated row assets outside Git preserves the frozen publication boundary.
- Two complete private candidates prove deterministic application and data packaging before any
  provider receives bytes.
- An inactive target is required to compare live files to the local manifest and rehearse rollback
  without replacing the aggregate release.
- Host-specific range, MIME, CORS, redirect, cache, quota, and cost behavior cannot be inferred from a
  loopback server or unrelated public files.

## Alternatives rejected

- Deploying the row candidate directly to the existing production Pages route was rejected because it
  would replace the supported aggregate product before live verification and final approval.
- Tracking generated row assets in Git was rejected because it would break the private publication
  boundary and repository size policy.

## Evidence

- Two candidates contain 38 files and 185,759,362 bytes each, below the 262,144,000-byte ceiling.
- Both candidates have the same private release digest; all 38 files replay byte-identically.
- The mart contains exactly 5,008,334 rows, 5,008,334 distinct valid opaque keys, 362,615 collision
  records, and 457,327 pending records. Exact aggregate reconciliation error is zero.
- All row values and packaged text have zero prohibited, credential, or private-path findings. The
  generated dictionary exposes exactly the 19 approved public fields.
- Local HTTP checks pass exact-origin CORS, 206 byte ranges, Parquet MIME, immutable cache headers,
  redirect refusal, missing-file refusal, and foreign-origin refusal.
- Ten browser query observations have a local p95 of 160 ms. Four cancellation and recovery sequences
  pass with no browser warnings or errors. A 390 by 844 viewport has zero page overflow and no unnamed
  controls in the checked page.
- The local candidate to aggregate-only to candidate rehearsal passes. Restoration uses a cache-busting
  navigation before accepting the restored hashed bundle.
- Local incremental provider cost is $0 because no provider action occurred.

## Remaining gates

- Record owner approval for one exact inactive target and its required provider mutation.
- Reverify current source terms immediately before public data activation.
- Upload only the verified manifest inventory and prove live file hashes, HTTPS, range, MIME, CORS,
  redirect, and immutable cache behavior.
- Run live reconciliation, browser latency, actual cost, quota, and provider rollback checks.
- Record the final publication decision before activating any public manifest.

## Not done

- No data, release candidate, or evidence was uploaded.
- No deployment, provider mutation, push, publication, or live-site replacement occurred.
- No claim is made that GitHub Pages or another public origin currently satisfies the live row-data
  contract.

## Changed

- The release state changed from implementation complete to a frozen private candidate awaiting one
  approved inactive target.
- The supported production product and public data boundary did not change.
