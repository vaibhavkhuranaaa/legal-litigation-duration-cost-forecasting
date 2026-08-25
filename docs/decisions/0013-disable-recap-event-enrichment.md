# Decision 0013: Disable RECAP event enrichment

Status: accepted

## Context

The retained CourtListener RECAP source is a complete docket-metadata bulk file. Promoted reconciliation links 2,065,537 dockets to collision-free FJC cases with reviewed precision above the match gate. The source schema contains docket filing and termination metadata but does not contain docket-entry number or description fields.

## Decision

Disable milestone-event enrichment. Do not infer event families from case names, nature text, docket-level termination dates, or other administrative metadata. Return `event_unavailable` with the missing fields and preserve observed portfolio and historical cohort alternatives.

## Why

An event label requires docket-entry evidence. Docket-level metadata cannot establish what procedural event occurred or when it occurred.

## Alternatives rejected

- Treating termination dates as event entries would conflate administrative closure with a procedural milestone.
- Inferring events from case names or nature text would fabricate labels.
- Downloading an unbounded new bulk source is unnecessary for the approved current-data release.

## Not done

No event golden set, precision, recall, or duration update is claimed.

## Changed

Milestone availability is now measured by a tested schema contract. Missing event-entry evidence returns a typed fallback.

## Consequences

Match coverage remains useful provenance for operational metadata but is not event coverage. No golden-set precision or recall is claimed because there are no event-entry candidates to label. A future event-entry source must receive a separate immutable manifest, timestamp validation, bounded labeling packet, and quality gate before this decision can change.
