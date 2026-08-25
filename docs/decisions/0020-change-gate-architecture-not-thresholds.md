# 0020: Change gate architecture, not failed thresholds

## Decision

Preserve every M7 numeric threshold and its negative evidence. Replace the inline Boolean release check with a frozen, capability-scoped policy that emits a complete gate ledger and independent capability states.

The individual-duration contract remains 5 percentage points overall calibration error at 365 and 730 days, 10 percentage points maximum supported-slice error, 80 percent estimate coverage, and 5 percent challenger integrated-Brier improvement with a positive paired-bootstrap lower bound. The policy is identified and hashed. Development-only evidence, incomplete metrics, invalid case accounting, or a digest mismatch cannot promote an estimator.

## Why

The held-out challenger improves average probability accuracy but fails reliability requirements. Relaxing thresholds after seeing those results would convert a measured failure into an unsupported claim. A typed gate ledger makes the same decision reproducible, reviewable, and enforceable by CI while allowing descriptive analytics to remain available.

## Temporal integrity

Future rolling-origin work must model what was knowable at the simulated prediction date. Adjacent filing cohorts are insufficient when validation labels mature after the next assessment begins. A future 365-day capability must embargo any calibration outcome not fully observed before its assessment origin and must retain the full eligible population in its coverage denominator.

## Consequences

- Individual intake duration remains blocked and returns no estimate.
- Descriptive analytics remains ready.
- A different aggregate or shorter-horizon claim requires a new capability identifier, target, validation protocol, and untouched final holdout.
- Threshold changes under the current policy identifier fail before model evaluation.

## Alternatives rejected

- Lower the coverage or slice threshold. Rejected as post-hoc gate weakening.
- Treat 12-month overall calibration as permission for individual predictions. Rejected because supported-slice reliability still fails.
- Score the sealed later cohort under an undeclared aggregate claim. Rejected because the estimand, temporal slices, label embargo, and uncertainty method are not frozen.
