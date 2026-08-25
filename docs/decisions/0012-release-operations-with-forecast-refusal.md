# Decision 0012: Release operations analytics with forecast refusal

Status: accepted

## Context

M7 protocol versions 1, 2, and 3 failed the unchanged duration-model gates. The official FJC case-level source also lacks the cutoff required for the sealed final holdout. On August 18, 2026, the owner approved completing the local product with current verified data rather than waiting for a future source release.

## Decision

Complete M8 through M14 as a non-predictive legal-operations release. Preserve every M7 failure and keep the sealed final outcomes unread. The product may expose observed portfolio analytics, historical cohort benchmarks, pending-inventory aging, provenance, data quality, and deterministic synthetic staffing and budget scenarios.

Duration forecast readiness remains false. Intake and milestone forecast requests return a typed refusal with the failed gates, unavailable source cutoff, and safe alternatives. Historical cohort summaries are labeled observed benchmarks, not predictions. RECAP metadata may enrich operational history only after its own quality checks; it may not update duration estimates.

## Why

Current data supports verified portfolio operations and provenance, while forecast gates do not pass. Typed refusal preserves useful current-data functionality without converting failed model evidence into a readiness claim.

## Alternatives rejected

- Waiting indefinitely for a future FJC release would leave verified operations data unused.
- Lowering model gates or removing difficult cohorts would invalidate the evaluation.
- Shipping failed estimates with a warning would still expose unsupported matter-specific forecasts.

## Not done

No estimator is promoted, no final holdout is read, and no deployment, publication, cloud mutation, or spending is authorized.

## Changed

M7 closes as a fail-closed product control. M8 through M14 may deliver operations analytics, observed benchmarks, synthetic scenarios, and forecast refusal.

## Consequences

M7 closes as a verified fail-closed control, not a passing estimator. M8 through M14 may proceed under revised acceptance criteria that require honest refusal behavior. No model artifact is promoted. Product remains not legal advice, budget scenarios remain synthetic, and deployment, spending, push, publication, and portfolio actions remain separately prohibited.
