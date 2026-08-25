# 0021: Reject the label-mature aggregate baseline

## Decision

Keep the proposed aggregate 12-month portfolio-resolution capability blocked. Preserve the development result and do not inspect the April through June 2024 final holdout.

## Why

Protocol v4 changes the target rather than weakening the individual-duration gates. It evaluates a three-year trailing national baseline across four rolling assessment periods. Only 365-day labels fully known before each simulated prediction date enter training. Assessment coverage is 100 percent, but all four folds fail the predeclared overall uncertainty and monthly calibration gates.

The result also exposes an important temporal-validation distinction: ordering cohorts by filing date does not prevent leakage when labels from the calibration cohort mature after the next assessment begins.

## Alternatives rejected

- Score the final cohort because one point estimate is below 5 percent. Rejected because every fold fails at least the uncertainty and monthly gates.
- Remove pandemic or mass-litigation months. Rejected as post-hoc scope selection.
- Lower the monthly threshold. Rejected because the threshold was frozen before the run.
- Train a challenger on the sealed cohort. Rejected because the final cohort is not development data.

## What changed

- Added a frozen aggregate capability contract and four label-mature rolling folds.
- Added clustered bootstrap uncertainty and filing-month calibration gates.
- Added an immutable-output development command and regression tests.
- Published aggregate-only failure evidence; no row-level data or model artifact entered Git.
