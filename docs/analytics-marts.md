# Analytics marts

M6 exposes six governed analytics products from the complete FJC statistical-record population, collision-free cases, and reviewed RECAP identity matches. All metrics use the March 31, 2026 FJC cutoff. RECAP match availability uses the retained June 30, 2026 snapshot and exact rule version 1.

| Mart | Grain | Decision supported | Core measures | Limitation |
| --- | --- | --- | --- | --- |
| Portfolio summary | District and nature family | Locate volume, pending inventory, and coverage concentrations | Total, pending, terminated, collision-free, supported-nature, and matched records | Counts describe public statistical records, not private matter workload |
| Filing cohorts | Filing year, district, and nature family | Compare intake cohorts and follow-up maturity | Cohort size, observed terminations, pending records, matches, and follow-up days | Recent cohorts have less follow-up |
| Pending inventory | District, nature family, and age band | Identify aging open-case inventory | Pending count, matched pending count, and average age | Age is measured at source cutoff and is not remaining duration |
| Duration summary | District, nature family, jurisdiction, origin, and procedural cohort | Assess support before modeling | Support, observed, censored, follow-up, and observed-duration averages | Observed-duration average excludes censored cases and is not a survival estimate |
| Comparable cases | One collision-free case | Supply intake-known records and support counts for M7 | Duration, event flag, intake grouping, procedural cohort, filing-law codes, snapshot diagnostics, match availability, and group support | Similar metadata does not establish legal comparability or advice |
| Data coverage | Overall, district, filing year, nature family, or procedural cohort | Decide where analytics and future updates are supportable | Total, collision-free, supported-nature, matched, and match coverage | Match coverage measures availability, not event completeness |

All aggregate marts reconcile to the 5,008,334-record statistical population. Comparable cases reconcile to the 4,645,719 collision-free case mart. Pending inventory preserves all 457,327 right-censored records. RECAP matches contribute only availability and provenance; FJC remains the duration source. The procedural cohort is diagnostic and does not remove MDL or other difficult matters. M7 evaluated Kaplan-Meier and XGBoost AFT, preserved their failed calibration gates, and keeps duration estimates disabled.
