# Model card: no promoted duration estimator

## Release status

No duration model is deployed or packaged. Kaplan-Meier and XGBoost AFT were required candidates;
neither passed the unchanged calibration, supported-slice, and coverage gates. Protocol versions 1,
2, and 3 are retained as negative evidence. The version-3 final holdout remains sealed.

The API therefore returns `forecast_unavailable` with failed-gate evidence. Readiness reports
operations analytics as ready and duration forecasting as unavailable.

## Intended use

The released product supports portfolio counts, explicitly historical cohort benchmarks, RECAP
metadata-availability disclosure, and synthetic staffing/budget sensitivities. It does not predict
an individual case, legal outcome, settlement, merits, workload, or cost and is not legal advice.

## Evaluation gates and limitations

Required gates were at most 5% overall calibration error at 12 and 24 months, at most 10% error for
supported held-out slices with at least 200 cases, and at least 80% estimate coverage. Promotion of
XGBoost additionally required a 5% integrated-Brier improvement with positive paired-bootstrap
evidence. Calendar shifts, MDL bulk administration, district 29/origin 13 personal-injury behavior,
and Social Security timing defeated supported-slice stability. Difficult cohorts were retained.

A new predictive protocol requires new case-level FJC data, intake-time evidence for every feature,
predeclaration before final outcomes, time-ordered development, and the same release gates unless a
new owner-approved scientific standard is adopted prospectively.
