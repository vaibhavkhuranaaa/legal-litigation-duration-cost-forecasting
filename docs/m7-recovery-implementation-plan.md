# M7 Recovery and Release Plan

## Non-negotiable boundary

Protocol versions 1 and 2 remain failed negative evidence. Protocol version 3 remains sealed. The release gates, populations, and final holdout cannot be changed after outcomes are read. Predictive work cannot proceed without a passing promoted estimator; the non-predictive operations release proceeds through capability-specific refusal contracts.

## Recovery milestones

### M7-R1: legal outcome and cohort contract

Status: complete. The copied March warehouse passed all 109 dbt nodes, including the new cohort derivation test.

- Define the target as FJC statistical termination, not a merits, settlement, fee, or client-work outcome.
- Preserve every eligible case and identify MDL, Social Security review, ordinary-original, and other procedural-origin cohorts from intake-known codes.
- Carry filing title and section codes for future research.
- Label current-snapshot jury-demand and MDL-docket fields as diagnostics only. They are not protocol-v3 features.
- Gate: dbt contracts and the cohort derivation test pass with zero exceptions.

### M7-R2: development-only legal diagnostics

Status: complete. The private development report covers 4,060,443 cases filed through March 31, 2024 and found zero duration or censoring exceptions.

- Measure duration and censoring invariants.
- Measure calendar drift for district 29, origin 13, personal-injury torts, Social Security, and MDL.
- Measure the Kaplan-Meier support fallback routes on the latest development fold.
- Restrict every query to filing cohorts ending March 31, 2024.
- Gate: zero duration or censoring semantic exceptions and a reproducible private report.

### M7-R3: sealed protocol-v3 access control

Status: complete. Unit tests cover authorized development access, early-source refusal, post-development refusal, and exhausted final-attempt refusal.

- Parse and validate the frozen protocol as executable policy.
- Refuse development reads after March 31, 2024.
- Refuse final scoring before a source cutoff of June 30, 2026 with 730 days of follow-up.
- Refuse a second final-score attempt.
- Gate: unit tests prove each authorization and refusal path.

### M7-R4: rolling-origin development evaluation

Status: implemented and failed as development evidence. Neither frozen estimator policy passed every fold, so final scoring remains prohibited.

- Run all four frozen development folds for Kaplan-Meier and XGBoost AFT.
- Learn support certification and calibration policy only from training and validation data.
- Report overall 12- and 24-month calibration error, every supported slice with at least 200 cases, estimate coverage, IBS, paired-bootstrap evidence, fallback route, and calendar drift.
- Retain difficult cohorts. A failure leads to a documented estimator or calibration change followed by another development run, not a changed test population.
- Gate: the selected policy passes the unchanged thresholds on every development assessment fold before final scoring is authorized.

| Fold | Estimator | 12-month error, max 5% | 24-month error, max 5% | Max slice error, max 10% | Coverage, min 80% | Decision |
|---|---|---:|---:|---:|---:|---|
| 2020 | Kaplan-Meier | 1.67% | 1.07% | 15.97% | 50.38% | Fail |
| 2020 | XGBoost AFT | 3.53% | 0.93% | 25.29% | 44.98% | Fail |
| 2021 | Kaplan-Meier | 4.62% | 7.27% | 25.92% | 86.89% | Fail |
| 2021 | XGBoost AFT | 3.11% | 2.60% | 31.06% | 88.42% | Fail |
| 2022 | Kaplan-Meier | 1.36% | 3.01% | 29.18% | 70.56% | Fail |
| 2022 | XGBoost AFT | 2.37% | 1.99% | 27.79% | 79.78% | Fail |
| 2023 | Kaplan-Meier | 2.38% | 1.12% | 58.13% | 58.53% | Fail |
| 2023 | XGBoost AFT | 1.76% | 1.33% | 50.03% | 64.98% | Fail |

Method: complete 365- and 730-day development assessment outcomes, 400 deterministic bootstrap replicates, positive-logit monotone validation calibration, and validation-certified fallback support. Limitation: this is development evidence, not final-holdout evidence or readiness. The paired challenger IBS improvement by fold was -2.21 percent, 0.33 percent, 0.12 percent, and 0.85 percent, below the 5 percent promotion requirement.

### M7-R5: fresh source and one final score

Status: source blocked as of August 18, 2026, and protocol-v3 development gates do not authorize final scoring.

- Acquire a new official FJC case-level cumulative snapshot through the immutable manifest-first loader.
- Build new versioned M3 through M6 artifacts. Do not overwrite March 2026 evidence.
- Verify a source cutoff on or after June 30, 2026 and a never-inspected April through June 2024 holdout.
- Execute exactly one final score.
- Gate: calibration error is at most 5 percent at 12 and 24 months, maximum supported-slice error is at most 10 percent, and estimate coverage is at least 80 percent.
- Promotion: XGBoost may be promoted only if both estimators pass and it improves IBS by at least 5 percent with a positive paired-bootstrap lower bound. Otherwise promote a passing Kaplan-Meier baseline.

### M7-R6: filing-time evidence review

Status: complete and negative. No retained candidate field is admissible as a new intake feature.

- The FJC codebook makes title, section, and subsection optional and does not establish their historical stability.
- The FJC research guide warns that quarterly records can be overwritten and identifies jury, class-action, pro se, and in-forma-pauperis values as mutable with limited quality control.
- Rule 38 permits a jury demand after the initial complaint. JPML transfer and centralization operate on pending actions, so a current MDL docket value is not a filing-time feature for the original action.
- FJC annual civil files are termination-year extracts, not historical intake snapshots.
- A validation-only marginal support diagnostic also fails the unchanged joint gate: the 2020 assessment fold reaches only about 34 percent coverage at a 10 percent marginal certification threshold.
- Gate: no field is admitted without primary timing evidence. Result: passed as a leakage-control decision, but it does not cure model readiness. See [decision 0011](decisions/0011-reject-unproven-intake-fields.md).

## Non-predictive release milestones

### M8: event-informed milestone updates

Status: complete. Event-field availability is measured and the API returns a typed no-event fallback because required entry data is absent. No legal conclusion is inferred from docket text.

### M9: synthetic operations scenarios

Status: complete. Deterministic staffing and budget scenarios expose bounded assumptions and explicit synthetic labels. They are never presented as observed bills or real cost forecasts.

### M10: service contracts

Status: complete. Versioned FastAPI contracts expose provenance, capability readiness, validation boundaries, and explicit refusal states. M7 model readiness remains false.

### M11: user interface

Status: complete. The accessible portfolio and matter-planning workflows show support, provenance, cohort limitations, synthetic labels, and visible refusal states.

### M12: reliability and security

Status: complete. Input, dependency, abuse, privacy, accessibility, recovery, and bounded reliability controls have passing release evidence.

### M13: offline demonstration

Status: complete. The container packages an aggregate SQLite seed, deterministic synthetic scenarios, and the built frontend without warehouse credentials, private records, case-level rows, or live BigQuery dependencies.

### M14: cold-start release gate

Status: complete for the local artifact. Tests, artifacts, model card, data quality, architecture, security, recovery, screenshots, and cost estimate passed the integrated gate. Publication is handled separately under the release gate.

## Current blocking fact

The latest located official FJC case-level cumulative snapshot ends March 31, 2026. The sealed final holdout ends June 30, 2024, so that snapshot supplies 639 days of follow-up, not the required 730. As rechecked August 18, 2026, the linked ZIP remains 326,678,495 bytes with ETag `"1378b7df-651b130012013"` and a May 13, 2026 last-modified timestamp, matching the retained immutable object. June 30, 2026 aggregate court tables do not contain case-level outcomes and cannot substitute for the cumulative research file.
