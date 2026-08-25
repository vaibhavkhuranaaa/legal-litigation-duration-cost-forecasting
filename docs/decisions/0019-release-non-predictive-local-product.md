# 0019: Release the non-predictive local product

Status: accepted

## Decision

Pass the integrated local release only when tests, lint, dbt lineage, frontend build, accessibility,
security boundaries, dependency review, deterministic seed, container cold start, provenance, and
typed forecast refusal agree. Release operations analytics and synthetic scenarios; do not release
duration predictions or milestone-event inference.

## Why

Verified operations capabilities remain useful even though duration and event evidence fails. A
capability-specific release avoids discarding valid analytics or overstating model readiness.

## Alternatives rejected

Calling failed models descriptive estimators would obscure their gate failures. Blocking every
operations workflow on an unrelated prediction failure would not reflect the tested API boundary.

## Not done

No model was promoted, no final v3 outcomes were opened, and no deployment, publication, push,
cloud mutation, paid action, or hosted service-level claim was made.

## Changed

Completed M8 through M14 evidence, documentation, release checks, aggregate container, capability
readiness, and typed refusals while preserving all M7 failures.

## Consequences

The product is locally reviewable and fully ready for its approved non-predictive scope. Deployment,
publication, cloud mutation, and predictive readiness remain separate approval gates.
