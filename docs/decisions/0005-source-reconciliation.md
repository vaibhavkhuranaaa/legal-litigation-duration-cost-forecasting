# Decision 0005: Fail-closed source reconciliation

Status: accepted

## Decision

Use the complete FJC statistical-record population for AO validation and only collision-free FJC cases for RECAP candidate generation. Generate candidates with an exact, versioned court, office, seven-digit docket core, and filing-date rule. Block collisions and conflicting evidence. Promote nothing until blinded review passes the 99.5 percent precision and confidence-bound gate with zero unresolved promoted collisions.

Use AO dates only to select Table C reporting cohorts. Preserve actual filing and termination dates for survival analysis. Compare the full FJC population to AO and bridge explicit product-scope exclusions rather than forcing equality.

## Why

FJC and RECAP are independently maintained sources. Shared-looking identifiers do not prove identity. The exact rule produces reviewable candidates while keeping source-provided IDB and PACER identifiers, termination, jurisdiction, and nature fields as independent corroboration.

The current FJC natural identifier collides for 362,615 statistical records. Excluding those records from automatic matching prevents invented deduplication. Reporting match coverage against both the collision-free denominator and the full population makes this limitation visible.

AO Table C and the retained FJC snapshot have a common March 31, 2026 reporting cutoff. The full FJC counts pass the predeclared 0.5 percent national threshold, including exact pending-stock agreement. Small filing and termination differences are consistent with publication-version lag, but that explanation remains a limitation rather than row-level proof.

## Alternatives rejected

- Trust `idb_data_id`, PACER identifiers, names, judges, nature text, or termination dates as identity keys. These fields are absent, derived, mutable, or not jointly authoritative.
- Fuzzy-match case or party names. This adds privacy exposure and an unjustified false-match path.
- Resolve FJC collision groups by row order or apparent recency. No retained authority defines such a winner.
- Optimize coverage by weakening precision. Milestone updates are optional enrichment; incorrect attachment is worse than abstention.
- Treat aggregate AO agreement as evidence of row-level matching. Aggregate definitions and identity are separate claims.

## Not done

FJC natural-key collision groups and candidate evidence conflicts remain blocked. Match review does not validate RECAP event families, event dates, unmatched completeness, or future milestone-update quality. No CourtListener API, BigQuery query, GCS operation, cloud reconciliation, deployment, spending, push, or publication occurred.

## Changed

Added a strict private RECAP extractor with field-count quarantine, a versioned 94-district crosswalk, exact candidate and ambiguity marts, complete-population AO Table C reconciliation, a product-scope bridge, a deterministic blinded review packet, and an exact-binomial evaluator. Governed review passed with 800 true matches, a 99.54 percent exact lower bound, and zero promoted collisions. Added fail-closed promotion plus overall, district, filing-year, and nature-family coverage evidence without placing source data or private review state in public Git.
