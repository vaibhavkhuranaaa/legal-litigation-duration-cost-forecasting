# 0001 Governed foundation and product rebaseline

## Decision

Rebaseline repository as Federal Civil Litigation Operations and Duration Planner. Keep public Git free of delivery state and datasets. Treat prior three-court resolved-only implementation and its metrics as private legacy evidence. Establish Python 3.12, dbt, FastAPI, React, and public data contracts before acquisition.

## Why

Approved product needs nationwide censored duration analytics, reviewed RECAP enrichment, calibrated survival estimates, and dual-persona workflow. Prior implementation cannot support those claims and current-looking legacy evidence would mislead reviewers.

## Alternatives rejected

- Extend prior resolved-only cohort. It omits open cases, most districts, and required model gates.
- Use CourtListener as population. Its event and docket coverage is uneven.
- Keep old metrics in public tree with warnings. Warnings do not prevent accidental current claims.
- Reconcile or apply Terraform during foundation. Cloud state conflicts require separate approval and evidence.

## Not done

No FJC download, cloud query, Terraform action, modeling, full API, interface, deployment, spend, push, publication, or portfolio change.

## Changed

Moved private records, local datasets, and Terraform state out of public folder; removed current-looking legacy implementation artifacts; added product contracts, toolchain declarations, public-boundary check, and decision-ready architecture and metric documentation.
