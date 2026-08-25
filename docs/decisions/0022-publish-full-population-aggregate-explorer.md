# Decision 0022: Publish a full-population aggregate explorer

Date: 2026-08-25

## Decision

Replace the four-constant browser demonstration with a deterministic analytical cube generated from
the complete governed warehouse population. Publish exact national and marginal totals and supported
district-by-nature, filing-year, and pending-age cells. Require at least 200 records at the smallest
published grain and expose the threshold, source snapshot, support, and limitations in the product.

## Boundary

The public artifact contains zero matter-level rows. It excludes case and source identifiers, docket
numbers, exact filing dates, parties, judges, attorneys, document text, source archives, warehouse
files, and model artifacts. Descriptive duration averages apply only to observed terminations and are
never presented as duration forecasts.

## Rationale

The full warehouse supports materially richer portfolio operations analysis without requiring raw
records in a public static application. Exact parents retain the complete population while thresholded
leaf publication reduces disclosure and misinterpretation risk. The same versioned artifact serves
GitHub Pages and the offline API, which prevents static and container demonstrations from drifting.

## Consequences

The public client can filter 94 districts and 14 nature families, inspect 17 filing-year cohorts and
four pending-age bands, and export the active evidence view. The release adds deterministic
reconciliation, schema, suppression, identifier-denial, API, frontend-build, and container checks.
