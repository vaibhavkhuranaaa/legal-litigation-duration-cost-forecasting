# Decision 0010: Preserve protocol-v3 development failure and keep final outcomes sealed

Status: accepted

## Context

The frozen protocol-v3 implementation ran all four rolling-origin development folds against the read-only March 2026 warehouse. It used intake-only features, positive-logit monotone calibration fitted on each validation window, validation-certified support routes, deterministic seeds, and the unchanged release gates. It did not query the April through June 2024 final holdout.

## Result

Neither estimator passed all development folds. Overall calibration often passed, but maximum supported-slice error ranged from 15.97 to 58.13 percent for Kaplan-Meier and 25.29 to 50.03 percent for XGBoost AFT. Coverage ranged from 50.38 to 86.89 percent and 44.98 to 88.42 percent respectively. The required thresholds remain 5 percent overall calibration at each horizon, 10 percent maximum supported-slice error, and 80 percent coverage.

## Decision

Preserve the run as negative development evidence. Do not score the final holdout, promote either estimator, begin M8, weaken a gate, or remove an outcome-difficult legal cohort. The current data supports descriptive portfolio analytics and exposes genuine procedural heterogeneity, but it does not support a release-ready individual duration estimate.

## Consequences

Further recovery requires evidence that a proposed filing-time feature is truly available and stable at intake, plus a new predeclared development policy before any final outcome read. A fresh FJC case-level snapshot at or after June 30, 2026 is also still required. Aggregate court tables cannot satisfy that requirement.
