# Decision 0009: Govern legal procedural cohorts without changing protocol v3

Status: accepted for development diagnostics

## Context

Protocol version 2 failed supported-slice calibration even though its challenger improved overall IBS. Development evidence also shows major calendar differences in MDL, Social Security, district 29, and origin 13 populations. Treating all of these records as one undifferentiated legal population hides a material limitation.

## Decision

Derive an intake-known procedural cohort from origin and canonical nature codes, expose it in governed marts, and report it in development diagnostics. Preserve every eligible record and the frozen protocol-v3 feature list. Carry filing-law codes for research, but classify current-snapshot jury and MDL-docket values as diagnostic-only fields.

The target remains FJC statistical termination. Public product language must not equate it with settlement, merits resolution, legal-work completion, or cost.

## Consequences

The assessment can now distinguish population drift from estimator error and quantify where fallback routes are used. The cohort cannot be used to remove difficult cases from the sealed final holdout. Adding any field to a later protocol requires new timing evidence, a new predeclaration, and a fresh holdout.
