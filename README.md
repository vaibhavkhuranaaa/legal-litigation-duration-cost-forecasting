# Federal Civil Portfolio Intelligence

[![Quality](https://github.com/vaibhavkhuranaaa/legal-litigation-duration-cost-forecasting/actions/workflows/quality.yml/badge.svg)](https://github.com/vaibhavkhuranaaa/legal-litigation-duration-cost-forecasting/actions/workflows/quality.yml)

[Open the full-population analytics dashboard](https://vaibhavkhuranaaa.github.io/legal-litigation-duration-cost-forecasting/). It runs entirely in the browser from a thresholded analytical cube built from all 5,008,334 governed records; no case-level data or duration model is shipped.

## Next release plan

The next release will extend this aggregate fast path with an identifier-minimized analytical mart
containing the complete 5,008,334-record snapshot, queried in the browser through DuckDB-WASM and
presented as an eight-page, Power BI-style report workspace. The mart will preserve collision records
and expose only approved analytical fields. Docket identifiers, names, text, private review evidence,
and model artifacts remain excluded.

This capability is planned, not live. The milestone sequence, publication contract, architecture,
performance targets, cost boundary, and exact first implementation slice are in the
[row-level analytics release plan](docs/row-level-analytics-plan.md). Generated data will remain out
of tracked Git and cannot be published until the new release gates pass.

Ready portfolio product for nationwide federal civil operations analytics and synthetic planning. It
includes verified acquisition, a replayable raw platform, a tested dbt warehouse, governed marts,
typed FastAPI contracts, an accessible React interface, and an offline full-population container.
Raw data and warehouses remain private. Duration forecasts are disabled because model gates failed.

## What it does

The product supports three decisions:

- Legal-operations leaders review federal civil portfolio duration, pending inventory, coverage, and calibration.
- Analysts filter the complete governed population across 94 districts, 14 nature families, 17 filing years, and four pending-age bands; cells below 200 records are withheld.
- Operations teams compare workload concentration, backlog aging, observed cohorts, evidence coverage, and clearly synthetic resource and budget scenarios within one governed analytical scope.

Outputs use public court metadata, preserve open cases through right censoring, show provenance, and refuse unsupported forecasts. Product is not legal advice. Historical benchmarks are not predictions. Synthetic budget scenarios are not observed billing or real cost forecasts.

## Architecture

FJC IDB is the population backbone. CourtListener RECAP is gated enrichment. U.S. Courts and AO
tables provide aggregate validation. Python 3.12 and Polars handle acquisition and bounded
processing; dbt Core builds the private canonical warehouse and marts. FastAPI and React with
TypeScript, Vite, and ECharts form the product layer. The local release reads only a deidentified,
aggregate SQLite seed and a versioned, identifier-free population cube. It packages no model,
warehouse, source dataset, or cloud credential.

See [architecture](docs/architecture.md), [data contract](docs/data-contract.md), [analytics marts](docs/analytics-marts.md), [intake survival evaluation](docs/survival-model.md), and the [M7 recovery and release plan](docs/m7-recovery-implementation-plan.md).

## Evaluation

Release gates are specified before modeling:

- At least 99.5 percent reviewed FJC and RECAP match precision.
- Zero unresolved promoted match collisions.
- Overall 12-month and 24-month calibration error at most 5 percentage points.
- Supported slices with at least 200 cases at most 10 percentage points calibration error.
- At least 80 percent estimate coverage among eligible cases.
- XGBoost AFT needs at least 5 percent integrated Brier score improvement over Kaplan-Meier with acceptable bootstrap evidence.

Source reconciliation verified 100 percent reviewed precision across 800 blinded items, with a two-sided 95 percent exact-binomial lower bound of 99.54 percent and zero promoted collisions. The survival challenger improves integrated Brier score by 13.77 percent, but baseline and challenger both fail required 24-month and supported-slice calibration. Intake estimates therefore remain disabled. AO aggregate validation is measured separately and does not establish cross-source identity. See [metric glossary](docs/metric-glossary.md), [source reconciliation](docs/source-reconciliation.md), and [survival evaluation](docs/survival-model.md).

## Limits

- No source or case-level dataset is tracked in Git. The approved public artifact contains aggregate evidence only.
- No real legal-cost data is used.
- No FJC and RECAP match is assumed.
- No judge, party, attorney, document-text, legal-outcome, or legal-advice feature is included.
- Existing GCP resources and local Terraform state require reconciliation before any future cloud action.
- The release supports a static public dashboard and an offline container; a live production data service and autoscaling are outside its verified scope.

## Scaling

The seeded demo runs offline from a deidentified SQLite extract and a 1.8 MB aggregate cube derived
from the complete governed population, without BigQuery credentials or live warehouse queries.
The planned static-lakehouse extension retains the aggregate cube for initial rendering and adds
partitioned Parquet only after browser and hosting benchmarks pass. It remains outside the current
release until M22.

## Current checks

```sh
uv run ruff check .
uv run pytest -q
uv run python scripts/check_public_boundary.py
uv run python scripts/check_secrets.py
npm --prefix frontend run build
docker build -t federal-civil-planner:local .
docker run --rm -p 8080:8080 federal-civil-planner:local
```

M2 pins and validates current FJC population, FJC documentation, aligned AO validation tables, and retained CourtListener enrichment without placing source data in public Git. M3 converts the full FJC source into private filing-year Parquet with byte-level field selection, strict selected-field decoding, stable quarantine, exact row accounting, atomic promotion, and immutable replay. The verified local run accounts for 10,857,396 source rows: 5,008,334 eligible records from 2010 onward, 5,848,424 earlier exclusions, and 638 structural quarantines.

M4 builds all 5,008,334 eligible statistical records through dbt, preserves 457,327 pending records with right censoring, and isolates natural-key collisions rather than deduplicating them. The collision-free case mart contains 4,645,719 records. A separate exception mart preserves 362,615 records across 173,524 colliding identifiers. Exact codebook mapping supports 5,007,787 records; 547 records with 14 legacy nature-of-suit codes remain explicitly unsupported. These are warehouse data-quality results, not model-performance claims. See [canonical warehouse](docs/canonical-warehouse.md).

M5 validates the complete FJC population against AO Table C for the 12 months ending March 31, 2026. National FJC counts are 339,754 filed, 276,113 terminated, and 462,223 pending. Each comparison passes the predeclared 0.5 percent relative-difference gate, with exact pending agreement. Separately, governed review promoted 2,065,537 exact RECAP matches with zero unresolved collisions. Coverage is 44.46 percent of collision-free cases and 41.24 percent of the full statistical population. Match review establishes precision for the exact rule, not completeness or event quality.

M6 provides contracted portfolio, filing-cohort, pending-inventory, duration-summary, comparable-case, and data-coverage marts. Aggregate marts reconcile to all 5,008,334 statistical records, pending inventory reconciles to all 457,327 right-censored records, and comparable cases reconcile to all 4,645,719 collision-free cases. Observed-duration averages are descriptive only.

The public explorer consumes those complete marts rather than a sample. It publishes exact nationwide and one-dimensional totals, plus district-by-nature, annual filing, and pending-age cells with at least 200 records. The build verifies 94 districts, 14 nature families, 17 filing years, all 457,327 pending records, zero matter-level rows, stable ordering, and exact national reconciliation.

M7 evaluates Kaplan-Meier and XGBoost AFT on 329,617 later-filed held-out cases. Kaplan-Meier records 4.86 percent calibration error at 12 months and 11.47 percent at 24 months. XGBoost records 1.74 percent and 8.09 percent respectively. Both fail the supported-slice gate. Protocol-v3 development also fails slice and coverage gates without reading its final holdout. A separate label-mature aggregate baseline failed every rolling development fold, so its final holdout remains sealed. Frozen policy code, capability-specific readiness, and reason codes preserve those failures while authorizing the non-predictive operations release.

M8 through M14 complete that release: milestone events fail closed when required entry data is
absent; scenarios are explicitly synthetic; the API exposes ten versioned contracts; the
responsive interface passed zero-violation accessibility checks; reliability and security controls
are tested; the analytics application runs as an unprivileged, network-independent container; and the
integrated release gate passes. See [offline demo](docs/demo.md), [model card](docs/model-card.md),
[data quality](docs/data-quality.md), and [security review](docs/security-review.md).
