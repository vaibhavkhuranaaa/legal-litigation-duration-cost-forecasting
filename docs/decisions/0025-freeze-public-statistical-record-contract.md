# Freeze the public statistical-record contract

Status: implemented locally for M15. This decision authorizes contract-bound M16 and M17 work only.
It does not authorize data upload, deployment, push, publication, or public download activation.

## Decision

Freeze `public-row-mart.v1` at one governed FJC statistical record, not one guaranteed unique legal
case. Retain all 5,008,334 version-1 records, including all 362,615 collision records and all 457,327
pending records. Label collisions with `identity_quality_status` and `source_record_count`; never
deduplicate or represent them as canonical cases.

Publish district and circuit geography, but exclude office code. Replace exact filing and termination
dates with first-of-month values named `filed_month` and `terminated_month`. Publish the common source
snapshot cutoff, descriptive duration in days, governed administrative categories, quality states,
and reviewed RECAP match availability. Exclude exact event dates, docket and source identifiers,
names, text, review evidence, credentials, private paths, and models.

Create `release_record_key` as the first 128 bits of HMAC-SHA-256 over opaque-key version, immutable
dataset version, and private source-record identifier. Require a private release secret of at least 32
bytes. Keys are deterministic for an identical approved replay and stable only within one dataset
version. The secret and private input never enter public artifacts.

Freeze manifest version 1 with exact dataset, schema, snapshot, attribution, terms, null, date,
opaque-key, metric-registry, application-compatibility, partition, byte-size, row-count, and SHA-256
fields. Ordinary queries may return at most 10,000 rows and may not fetch all partitions. CSV exports
are formula-safe and capped at 50,000 rows. Filtered Parquet and full downloads require separate,
explicit user actions.

## Why

District, month, governed case categories, and descriptive elapsed time support planned portfolio
analysis. Office and exact event dates add linkability without enough decision value. A keyed,
release-scoped row reference supports drill-through and deterministic replay without publishing a
source or natural identifier. Complete collision retention preserves the source grain and prevents a
false one-row-per-case claim.

The Federal Judicial Center states that it provides public access to the IDB, but its official IDB
page does not state a standalone redistribution license. CourtListener terms require lawful use,
honest attribution, no implied endorsement, and no consumer-reporting use. The contract therefore
requires attribution and a use notice, and keeps public row-data download activation blocked until
M22 reverifies current source terms and records fresh owner approval.

## Alternatives rejected

- Publish office and exact dates. Rejected because their joinability outweighs their incremental
  analytical value.
- Hash a docket or natural key without a secret. Rejected because dictionary and linkage attacks
  would recover stable source identity.
- Assign a canonical winner within collision groups. Rejected because no retained authority defines
  one correct case row.
- Treat public source access as an unrestricted redistribution license. Rejected because the official
  source page does not make that grant.
- Allow default full-dataset queries. Rejected because normal report interactions need bounded
  partition and column reads.

## Not done

- No Parquet partition, row-data manifest, warehouse, or dataset was generated or placed in Git.
- No M17 browser benchmark, M16 full mart, semantic registry, report workspace, or record explorer was
  implemented.
- No source data was uploaded, deployed, pushed, published, or made public.
- No duration, event, outcome, cost, staffing, or legal prediction was enabled.

## Changed

- Added the executable `public-row-mart.v1` contract and fail-closed validation helpers.
- Added representative contract tests for field, key, collision, date, null, prohibited-content,
  manifest, export, attribution, and download-term rules.
- Replaced proposed office and exact-date fields with a denied office field and month-level event
  periods in the serving-mart dictionary.
- Added the M15 threat review and frozen source-use notices.

## Consequences

- M17 can build one private representative annual partition against a complete, executable contract.
- M16 must apply the same schema, key, collision, null, date, manifest, and prohibited-content checks
  to every final partition.
- M21 must repeat linkability and security review against physical artifacts and browser behavior.
- M22 remains the only gate that can authorize public row-data activation.
