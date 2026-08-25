# 0003 Replayable raw platform

## Decision

Convert the FJC cumulative civil snapshot into private, immutable Parquet with a versioned raw contract. Select approved metadata fields at the byte boundary, exclude party and judge fields, require strict UTF-8 for selected values, partition eligible 2010 onward cases by filing year, and quarantine structural or row-contract failures. Define create-only GCS and BigQuery load plans without executing them.

## Why

The source contains invalid text bytes in excluded party fields and malformed tabular rows. Byte-level field selection prevents those values from entering the product while preserving approved metadata exactly. Explicit exclusion and quarantine counts make the full input population auditable. Content-addressed output, deterministic plans, atomic promotion, and no-op replay prevent silent overwrite.

## Alternatives rejected

- Decode the full source with a permissive codec. This would silently reinterpret excluded text and would accept malformed rows.
- Partition by source reporting year. Pending cases use a future sentinel reporting year, so filing year is the reliable physical partition.
- Calculate duration and censoring in raw conversion. Those governed semantics belong in the canonical dbt warehouse.
- Reuse legacy BigQuery tables. Their current state is unverified and their layouts do not meet the current contract.
- Upload or query cloud resources now. Live reconciliation, cost, IAM, and mutation remain approval gated.

## Not done

No cloud API call, upload, query, load, provision, IAM change, Terraform action, dbt transformation, duration calculation, nature-of-suit mapping, source match, model training, deployment, spend, push, or publication occurred.

## Changed

Added a bounded Polars raw converter, private-output enforcement, stable quarantine reasons, full-row reconciliation, filing-year partitions, run metrics, idempotent replay, failure recovery, deterministic cloud plans, tests, and operating documentation.
