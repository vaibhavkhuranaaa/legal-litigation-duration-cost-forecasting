# Decision 0006: Governed analytics marts

Status: accepted

## Decision

Build six dbt marts for portfolio, filing-cohort, pending-inventory, duration, comparable-case, and data-coverage consumers. Keep complete statistical records as aggregate denominator, use collision-free cases for record-level comparables, and use promoted RECAP matches only as an availability flag. Preserve open cases and support counts everywhere they affect later modeling.

## Why

Legal-operations decisions need stable, tested grains before models or interface logic exist. Separating aggregate population views from collision-free record-level comparables prevents natural-key exceptions from disappearing. Explicit match coverage prevents optional RECAP enrichment from being mistaken for complete population evidence.

## Alternatives rejected

- One wide mart. It would mix record, cohort, and portfolio grains and invite double counting.
- Resolved-only duration summaries. They would hide right censoring and bias the population boundary.
- RECAP as duration source. FJC remains the governed population and duration source; RECAP event quality is not validated yet.
- New semantic-layer dependency. dbt contracts, exposures, and focused singular tests cover current consumers.

## Not done

No Kaplan-Meier baseline, challenger model, event-family extraction, API, interface, cloud query, deployment, spending, push, or publication occurred. Observed-duration averages remain descriptive and cannot be presented as duration estimates.

## Changed

Added six contracted marts, promoted-match staging, two consumer exposures, compound-grain checks, full aggregate reconciliation, metric documentation, and explicit support and limitation fields.
