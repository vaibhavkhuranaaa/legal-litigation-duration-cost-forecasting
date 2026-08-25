# Intake survival evaluation

## Decision

The duration capability remains unavailable, while the product is ready for its approved
non-predictive operations scope. Neither evaluated estimator may provide an individual intake
duration estimate.

The Kaplan-Meier baseline passes 12-month overall calibration and estimate coverage, but fails 24-month calibration and supported-slice calibration. The XGBoost accelerated failure time challenger improves probability accuracy, but it also fails those two gates. The release policy does not permit the challenger to bypass a failed baseline.

## Population and chronology

Evaluation uses collision-free cases from `mart_comparable_cases` and preserves pending cases as right-censored observations. Protocol version 2 fixes the following calendar split:

| Cohort | Filing dates | Cases | Use |
| --- | --- | ---: | --- |
| Training | 2010-01-01 through 2022-03-31 | 3,464,976 | Kaplan-Meier history and AFT fitting |
| Validation | 2022-04-01 through 2023-03-31 | 265,850 | AFT early stopping and calibration |
| Held-out | 2023-04-01 through 2024-03-31 | 329,617 | Final comparison |

The March 31, 2026 source cutoff gives every validation and held-out case complete administrative follow-up through 730 days. Censoring-aware training still preserves all pending cases.

## Feature contract

Both estimators use information known at filing:

- district code
- canonical nature family
- jurisdiction code
- origin code
- filing year for the challenger

RECAP matches, docket events, termination fields, party names, judge identity, disposition, and every post-filing field are excluded. Unsupported nature codes receive an abstention rather than an invented mapping.

The Kaplan-Meier baseline uses recent training history from April 1, 2019 through March 31, 2022. It selects the most specific group with at least 500 training cases and falls back through declared intake-known groupings. The challenger uses XGBoost's censoring-aware AFT objective and a validation-fitted log-normal calibration transform.

## Held-out results

| Metric | Gate | Kaplan-Meier | XGBoost AFT |
| --- | ---: | ---: | ---: |
| 12-month calibration error | at most 5% | 4.86% | 1.74% |
| 24-month calibration error | at most 5% | 11.47% | 8.09% |
| Maximum supported-slice calibration error | at most 10% | 77.81% | 52.52% |
| Estimate coverage | at least 80% | 100.00% | 100.00% |
| Integrated Brier score | lower is better | 0.21465 | 0.18510 |

The challenger's relative integrated Brier improvement is 13.77%. Its case-paired bootstrap 95% interval is 13.63% to 13.91%, above the required 5% improvement. Complexity is still rejected because probability improvement cannot compensate for failed calibration.

Large calendar shifts in several cohorts drive the failure. District 29 has 57,821 held-out cases and a 77.81% Kaplan-Meier calibration error at 24 months. Removing a difficult district after seeing held-out results would change the nationwide product scope and invalidate the evaluation. The model therefore abstains globally until a new protocol and a fresh complete holdout are available.

## Interpretation boundary

These are retrospective public-metadata estimates, not legal advice, case-outcome predictions, or real cost forecasts. Even a future calibrated model would describe uncertainty for similar historical cohorts, not determine how long a particular matter will last.

## Recovery status

Protocol versions 1 and 2 remain failed evidence. Protocol version 3 was sealed on August 17, 2026 without reading outcomes for filings after March 31, 2024. Its final holdout covers April through June 2024 and requires an official FJC cumulative civil cutoff of at least June 30, 2026 for complete 730-day follow-up.

The official cumulative civil asset available on the declaration date remained the March 31, 2026 snapshot. The AO subsequently posted June 30 aggregate civil tables, but FJC's cumulative ZIP, annual FY2026 dataset, five-year dataset, ten-year dataset, and interactive database still stop at March 31. Aggregates do not contain the case-level outcomes needed for the frozen cohort gate. Version 3 therefore has not been scored and no estimator is promoted. Predictive updates remain blocked, while decision 0012 permits non-predictive operations capabilities to proceed behind typed refusals. See [decision 0008](decisions/0008-seal-m7-recovery-protocol.md) and [decision 0012](decisions/0012-release-operations-with-forecast-refusal.md).

The executable protocol guard refuses development outcomes after March 31, 2024, final scoring from a source earlier than June 30, 2026, and any second final-score attempt. Legal procedural cohorts are development diagnostics and do not alter the frozen feature set or test population.

The four-fold protocol-v3 development implementation also failed. Overall calibrated errors often met their gates, but maximum supported-slice error remained between 15.97 and 58.13 percent for Kaplan-Meier and 25.29 and 50.03 percent for XGBoost AFT. Coverage also fell below 80 percent in three baseline folds and three challenger folds. These results use validation-fitted monotone calibration and validation-certified support, with no final-holdout read. Final scoring is therefore prohibited even if a qualifying source appears until a scientifically valid predeclared recovery policy passes development. See [decision 0010](decisions/0010-preserve-v3-development-failure.md), the [legal cohort contract](legal-cohort-contract.md), and the [recovery implementation plan](m7-recovery-implementation-plan.md).

The subsequent filing-time evidence review rejected current-snapshot title, section, subsection, jury-demand, class-action, MDL-docket, pro-se, and in-forma-pauperis values as recovery features. Official documentation either makes them optional, permits them to change after filing, or does not establish their filing-time stability. Annual FJC datasets are termination-year extracts and cannot repair that evidence gap. See [decision 0011](decisions/0011-reject-unproven-intake-fields.md).
