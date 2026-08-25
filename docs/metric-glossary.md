# Metric glossary

| Metric | Definition | Direction | Release threshold | Decision |
| --- | --- | --- | --- | --- |
| Reviewed match precision | Correct promoted matches divided by reviewed promoted matches | Higher | At least 99.5% | Permit RECAP enrichment |
| Unresolved collisions | Promoted FJC cases with multiple unresolved candidates | Lower | 0 | Permit canonical promotion |
| Match coverage | Eligible FJC cases with promoted RECAP match divided by eligible FJC cases | Report | No minimum | State milestone-update availability |
| 12-month calibration error | Absolute observed minus estimated termination probability at 12 months | Lower | At most 5 percentage points overall | Ship intake estimates |
| 24-month calibration error | Absolute observed minus estimated termination probability at 24 months | Lower | At most 5 percentage points overall | Ship intake estimates |
| Supported-slice calibration error | Maximum 12-month or 24-month error for supported slices with at least 200 cases | Lower | At most 10 percentage points | Define supported slices |
| Estimate coverage | Eligible cases receiving supported estimate divided by eligible cases | Higher | At least 80% | Decide planner usefulness |
| Integrated Brier improvement | Relative held-out reduction from XGBoost AFT versus Kaplan-Meier | Higher | At least 5% with acceptable bootstrap evidence | Select challenger |

## Verified reconciliation results

| Metric | Baseline | Result | Method and limitation | Decision |
| --- | --- | --- | --- | --- |
| Reviewed match precision | 0% trusted matches | 100% across 800 items; 99.54% two-sided 95% exact lower bound | Stratified blinded review of exact-rule candidates; measures precision, not completeness | Permit exact-rule RECAP identity enrichment |
| Unresolved collisions | No promoted matches | 0 across 2,065,537 promoted pairs | One-to-one audit after blocking collisions and evidence conflicts; does not recover excluded candidates | Permit canonical promotion |
| Match coverage | 0% promoted | 44.46% of collision-free cases; 41.24% of full statistical population | Reported overall and by district, filing year, and nature family; no minimum and never optimized by weakening precision | Disclose where later milestone updates can be supported |

M7 verifies the model metrics on a time-ordered held-out cohort. Kaplan-Meier calibration error is 4.86 percent at 12 months and 11.47 percent at 24 months. XGBoost AFT calibration error is 1.74 percent and 8.09 percent. Worst supported-slice errors are 77.81 percent and 52.52 percent. Both estimators therefore fail release calibration. XGBoost improves integrated Brier score by 13.77 percent with a case-paired bootstrap 95 percent interval from 13.63 percent to 13.91 percent, but improvement does not override failed calibration. See [intake survival evaluation](survival-model.md).

## Planned row-level release metrics

These targets govern M15 through M22. They have no verified result yet.

| Metric | Definition | Direction | Planned threshold | Decision |
| --- | --- | --- | --- | --- |
| Publication contract coverage | Proposed public fields with a recorded classification divided by all proposed fields | Higher | 100% | Freeze M15 schema |
| Prohibited public fields | Denylisted fields found in the candidate mart | Lower | 0 | Permit mart promotion |
| Statistical-record reconciliation | Released rows divided by the 5,008,334-row version-1 snapshot expectation | Exact | 100% | Accept version-1 mart |
| Collision retention | Released collision records divided by 362,615 expected collision records | Exact | 100% | Preserve source truth |
| Record-key uniqueness | Distinct valid release keys divided by released rows | Exact | 100% | Permit row references |
| Aggregate reconciliation error | Maximum absolute difference between row-mart and approved-cube shared measures | Lower | 0 | Permit semantic release |
| Initial shell load | Largest Contentful Paint for the shell and aggregate overview on the frozen reference profile | Lower | At most 2.5 seconds | Accept initial experience |
| Cold filtered query p95 | 95th-percentile uncached time for the frozen representative query corpus | Lower | At most 3 seconds | Select browser architecture |
| Warm filtered query p95 | 95th-percentile cached time for the same corpus | Lower | At most 1 second | Accept interactive performance |
| Query bytes read | Network bytes required by each representative query | Report and bound | No unintended full fetch | Verify pruning |
| Peak browser memory | Maximum browser memory over the query corpus | Report and bound | No memory failure | Define supported profiles |
| Unbounded default queries | Record-explorer queries without a declared result ceiling | Lower | 0 | Permit explorer release |
| Accessibility violations | Automated accessibility violations across declared report states | Lower | 0 | Permit interface release |
| Recurring infrastructure cost | Actual recurring spend for the declared usage profile | Lower | $0 | Permit release under ceiling |

M17 must pin devices, browsers, network profile, query corpus, cache state, sample count, and measured
limitations before performance evidence can close a milestone.
