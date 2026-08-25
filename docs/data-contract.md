# Data contracts

## FJC population

The governed source grain is one FJC statistical record, not a presumed unique underlying case. All eligible records filed from 2010 through the selected complete reporting cutoff remain in the statistical-record mart. Open records remain in population with `event_observed = false`, `terminated_date = null`, and `censoring_date` equal to source cutoff.

The documented circuit, district, office, and docket key collides in the current source. Only keys observed exactly once enter the collision-free case mart. Every record associated with a repeated key enters the identity-exception mart and remains excluded from case-level consumers. M5 promotes reviewed cross-source matches only from the collision-free mart. No row is silently deduplicated. Source row position is provenance within an immutable source object, not a cross-snapshot case identity.

Required source fields include circuit, district, office, docket number, filing date, termination date where observed, nature of suit, jurisdiction, origin, disposition, procedural progress, and reporting period. Exact source names are pinned after acquisition.

### Raw boundary

Raw contract v3 selects 40 approved metadata fields at the byte boundary and excludes party and judge fields. Selected values must decode as UTF-8. It preserves source strings and keeps filing, termination, and AO-use dates separate. Eligible rows are filed from 2010-01-01 through the 2026-03-31 source cutoff and are physically partitioned by filing year. Rows before 2010 are explicit exclusions. Structural failures and invalid in-window status or date contracts enter private quarantine with source row references and no raw party text.

Raw conversion does not derive duration, censoring, canonical uniqueness, or nature-of-suit meaning. M4 owns those transformations and tests. Actual filing and termination dates define survival duration. AO-use dates remain separate for aggregate reconciliation.

### Warehouse boundary

The statistical-record mart preserves every accepted M3 record and labels its identity, nature-of-suit quality, and intake procedural cohort. The collision-free case mart exposes only natural identifiers with one source record. The identity-exception mart preserves every record from a collision group. dbt source, model, and singular tests enforce row reconciliation, status semantics, duration arithmetic, mapping status, cohort derivation, identity partitioning, and contracts.

M7 reads only the collision-free comparable-case mart. Its versioned contract fixes source cutoff, chronological split boundaries, maximum evaluation horizon, intake-known feature names, support thresholds, estimator parameters, bootstrap count, and release gates. Private artifacts retain evaluation results, estimator parameters, and categorical vocabularies. Because release gates fail, no scoring artifact is promoted to the public product or API.

The comparable-case mart identifies MDL, Social Security review, ordinary-original, and other procedural-origin cohorts without excluding records. Filing title and section codes remain research candidates. Current-snapshot jury-demand and MDL-docket fields are diagnostic only and are not protocol-v3 features. The target is FJC statistical termination, not settlement, merits resolution, fee, or client-work completion. See the [legal cohort contract](legal-cohort-contract.md).

The local DuckDB build is the verified development implementation. BigQuery remains the scaled target, but no BigQuery build, query, schema change, or cloud mutation is claimed.

## Nature-of-suit mapping

Mapping retains raw value, canonical code, family, source codebook date, and analytical rule version. It maps only the 93 exact codes retained in the current official codebook. Fourteen observed legacy codes covering 547 records are absent from that codebook and remain `unsupported`. The current codebook does not establish historical effective periods, so M4 makes no effective-dating claim. Unknown or malformed values remain explicit and cannot enter a supported estimate until reviewed.

## FJC and RECAP matching

Matching creates candidates, never truth. Candidate evidence includes court, office, normalized docket number, filing date, source identifiers, rule version, and collision count. Promotion requires at least 99.5 percent reviewed precision, a two-sided 95 percent exact-binomial lower bound at that threshold, zero unresolved collisions, reported coverage, and row-level provenance. Contract version 1 passed and promoted only one-to-one review-eligible candidates; collision and evidence-conflict rows remain blocked.

## Milestone events

Each event includes canonical case key, event family, date, RECAP docket entry ID, rule version, confidence, and provenance. Event families enter planner only after labeled validation and temporal leakage review. Documents, party data, attorney data, and free text do not enter public artifact.

## Seeded demo

Release artifact contains deidentified opaque keys, bounded analytical fields, precomputed outputs, metric metadata, and provenance summaries. It contains no raw docket number, PACER identifier, case name, party, attorney, judge, document text, cloud credential, or BigQuery access path.

## Public population cube

The version-1 cube is generated deterministically from the complete M6 portfolio, filing-cohort,
pending-inventory, and duration-summary marts. Exact national and one-dimensional aggregates retain
all 5,008,334 statistical records and all 457,327 pending records. District-by-nature, annual filing,
and pending-age cells publish only at support of at least 200. The schema allowlists aggregate
dimensions and additive measures; case identifiers, source identifiers, docket values, exact dates,
names, and document text are prohibited. Observed-duration averages use terminated cases only and
remain descriptive rather than censoring-aware estimates.
