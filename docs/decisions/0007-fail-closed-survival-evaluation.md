# 0007: Keep intake estimates disabled after survival evaluation

## Decision

Keep the product in descriptive-only mode. Preserve the evaluated Kaplan-Meier baseline and XGBoost AFT challenger as private evidence, but ship neither as an intake estimator.

Protocol version 2 uses a time-ordered train, validation, and held-out split; intake-known features only; right-censored training; complete 730-day evaluation follow-up; supported-slice checks; estimate coverage; and case-paired bootstrap comparison. The Kaplan-Meier baseline fails 24-month and slice calibration. The challenger clears the improvement gate but fails the same calibration gates. Release selection therefore resolves to `descriptive_only`.

## Why

The user decision requires reliable duration probabilities, not merely a lower average scoring loss. A 13.77% integrated Brier improvement does not make an 8.09% overall 24-month calibration error or 52.52% worst supported-slice error safe to present. The product contract explicitly says a failed baseline limits the product to descriptive analytics.

The initial protocol used only district and nature in its Kaplan-Meier grouping. It failed, and validation showed that instability was already observable. Version 2 corrected the grouping to use the mart's full intake-known cohort hierarchy. That correction did not rescue calibration. Because held-out results were inspected during this protocol correction, a future estimator requires a later complete snapshot for clean confirmation.

## Alternatives rejected

- Ship XGBoost because it beats Kaplan-Meier. Rejected because calibration and supported-slice gates are independent release requirements.
- Relax thresholds. Rejected because thresholds were approved before evaluation and represent the planning reliability contract.
- Remove districts or nature families after observing failure. Rejected because this is post-hoc scope selection and would no longer support the approved nationwide product.
- Drop pending cases and model only resolved durations. Rejected because it introduces survivorship bias and violates the censoring contract.

## What was not done

No intake endpoint, milestone-aware estimate, synthetic budget scenario, deployment, upload, cloud query, or public model artifact was created. Private data and model files remain outside Git.

## Consequence

M7 has complete negative evidence but does not pass its release metrics. M8 and other estimate-dependent milestones remain blocked until the owner approves a scientifically valid rebaseline that retains the gates and obtains a fresh holdout, or explicitly changes product scope.
