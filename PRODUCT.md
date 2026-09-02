# Product

## Platform

web

## Users

Legal-operations leaders and analysts monitor nationwide federal civil workload, inventory pressure, observed cohorts, and evidence coverage. Operations teams can separately test explicit synthetic staffing and budget assumptions.

## Product Purpose

Provide audit-friendly portfolio operations analytics from public court metadata. Success means users can understand pending inventory, historical cohort behavior, source coverage, forecast limitations, and scenario consequences without mistaking any output for legal advice or a matter-specific prediction.

## Positioning

The product makes failed evidence visible and useful: capability-level readiness permits verified operations analytics while typed refusals prevent failed duration models or absent docket events from becoming claims.

## Operating Context

Users work in portfolio reviews and analytical investigations. One governed scope connects nationwide measures, workload concentration, pending-age bands, observed cohort benchmarks, provenance, and forecast-refusal evidence. A separate scenario workspace handles synthetic resource sensitivities. Every measure carries source date, method, support, and limitation.

## Capabilities and Constraints

- Observed FJC portfolio, pending-inventory, and cohort analytics.
- Reviewed RECAP docket match coverage; docket-event enrichment disabled because event-entry fields are absent.
- Typed duration forecast refusal; no model artifact is promoted.
- Deterministic synthetic staffing and budget scenarios from bounded user assumptions.
- Static public dashboard and offline container; no live BigQuery, credentials, party, judge, attorney, or document-text data.
- Identifier-minimized statistical-record exploration with synchronized slicers,
  cross-filtering, drill-through, virtualized rows, column selection, and bounded export.
- Browser queries operate on immutable static assets through a read-only production origin and do not
  expose the private warehouse.
- Product is not legal advice. Historical benchmarks are not predictions. Scenario amounts are not real cost forecasts.

## Brand Commitments

Use plain operational language and the approved calm, precise, restrained, audit-friendly design language. Avoid courtroom drama, generic prediction certainty, and marketing filler.

## Evidence on Hand

- Verified FJC and AO population metrics documented in `README.md` and `docs/`.
- M7 model failures documented in `docs/survival-model.md`.
- M8 event availability documented in `docs/milestone-enrichment.md`.
- M9 scenario contract documented in `docs/synthetic-scenarios.md`.
- M10 API contract documented in `docs/api.md`.
- No testimonials, customers, observed legal-cost dataset, passing duration model, or live production-data service claim exists.

## Product Principles

1. Refusal is a first-class result.
2. Observed, modeled, and synthetic information never share an unlabeled visual treatment.
3. Every number remains auditable to source, method, period, support, and limitation.
4. Useful operations analytics may remain available when a separate capability fails.
5. Users retain legal and operational judgment.
6. Detail is earned through a publication contract, not by copying unrestricted source rows.

## Analytical release

M15 through M22 extend the aggregate cockpit into an eight-page analytical report while
preserving its visual language and capability truth. The current aggregate cube remains the initial
render and rollback path. The row-level mart includes the complete governed statistical-record
population but only approved analytical columns and release-scoped opaque keys. See the
[row-level analytics release plan](docs/row-level-analytics-plan.md).

## Accessibility & Inclusion

Target WCAG 2.2 AA contrast, keyboard operation, visible focus, semantic landmarks, reduced motion, responsive layouts, and text summaries for charts.
