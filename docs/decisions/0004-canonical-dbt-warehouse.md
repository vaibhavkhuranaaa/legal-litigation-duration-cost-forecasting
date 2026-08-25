# Decision 0004: Canonical dbt warehouse

Status: accepted

## Decision

Model the full FJC input as statistical records, then expose collision-free natural identifiers as cases and repeated identifiers as explicit exceptions. Preserve pending records with right censoring. Map only exact nature-of-suit codes supported by the retained official codebook. Use dbt Core contracts and tests with DuckDB as the local development target and BigQuery as the approval-gated scaled target.

## Why

The documented circuit, district, office, and docket key is not unique in the current source. Treating it as universally unique would discard or merge evidence. Source row position is stable only within one immutable source and cannot serve as a cross-snapshot case identity. Separating statistical records, collision-free cases, and exceptions keeps all source evidence while giving later reconciliation a fail-closed boundary.

Open records must remain in the population for survival analysis. Exact status and date rules preserve 457,327 pending records as right censored. The retained codebook supports nearly all records, but it does not define 14 observed legacy codes or establish historical effective periods.

Built-in dbt tests plus focused singular tests provide the required source, relationship, reconciliation, duration, identity, and mapping coverage without adding a package dependency. An isolated disabled model proves that CI catches an enforced contract violation.

## Alternatives rejected

- Deduplicate colliding natural identifiers by row order, reporting year, or termination date. Each rule invents a winner without source authority.
- Hash every business field into a case identifier. The result identifies a record version, not an underlying case, and can change across snapshots.
- Infer legacy nature-of-suit meaning from numeric ranges. The current codebook does not authorize that mapping.
- Add `dbt-expectations` for tests already expressed with built-in and singular tests. The additional dependency would not improve the current gate.
- Treat DuckDB results as proof of BigQuery execution. Adapter behavior and cloud layout remain unverified until an approved BigQuery run.

## Not done

No FJC and RECAP record matching, AO reconciliation, model training, BigQuery query, GCS load, cloud resource change, deployment, spending, push, or publication occurred. Colliding identifiers remain unresolved and unsupported legacy nature-of-suit codes remain unmapped.

## Changed

Added versioned dbt staging, intermediate, dimension, statistical-record, collision-free case, and identity-exception models. Added source freshness, schema contracts, relationships, accepted values, row reconciliation, censoring, duration, mapping, identity, and expected-failure checks. Added a private local DuckDB target pattern, generated private lineage documentation, and documented the scaled BigQuery boundary.
