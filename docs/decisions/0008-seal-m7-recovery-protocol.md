# 0008: Seal M7 recovery protocol pending a fresh official snapshot

## Decision

Keep protocol versions 1 and 2 as failed evidence. Seal protocol version 3 before reading any outcome for filings after March 31, 2024. Version 3 uses rolling-origin development folds, a final April through June 2024 holdout, intake-known features, cross-fitted monotone calibration, validation-derived support, fixed seeds, one final score, and unchanged release gates.

Do not score version 3 until an official FJC civil cumulative snapshot with a cutoff of at least June 30, 2026 is available. Do not start M8 until version 3 promotes a passing estimator.

## Why

The official FJC civil cumulative asset available on August 17, 2026 is unchanged from the retained March 31, 2026 snapshot. A same-day recheck after the AO published June 30 aggregate civil tables found that the FJC cumulative ZIP, annual FY2026 dataset, five-year dataset, ten-year dataset, and interactive database still stop at March 31. That cutoff provides only 729 days of follow-up for an April 1, 2024 filing and cannot support a fresh 730-day final cohort. AO aggregate tables and CourtListener records cannot replace FJC case-level outcomes.

Recovery diagnostics found correct duration and censoring arithmetic. Failure is dominated by calendar and cohort shifts, including a large Northern District of Florida multidistrict personal-injury cohort, not by a reversible target-construction defect. Recent-window, stability-filtered, and trend-adjusted Kaplan-Meier development trials did not satisfy all existing slice and coverage gates.

## Alternatives rejected

- Reuse the 2023-04-01 through 2024-03-31 cohort as final evidence. Its outcomes were inspected under version 2 and are development data now.
- Reduce the 730-day horizon. This changes an approved release gate.
- Substitute aggregate AO data or RECAP termination metadata. Neither is the governed FJC population outcome source.
- Remove difficult districts, origins, or nature families after observing errors. This is post-hoc scope selection.
- Promote XGBoost based on Brier improvement alone. Version 2 failed calibration gates.

## Not done

No final version 3 outcome was read, no estimator was promoted, and no M8 through M14 work began. No cloud, deployment, spending, push, publication, or visibility action occurred.

## Next evidence

The earliest qualifying cutoff is June 30, 2026. Once FJC publishes that cumulative civil snapshot, acquire it through the immutable manifest-first loader, rebuild versioned M3 through M6 artifacts, run version 3 development gates, and score the sealed final holdout once.
