# Centralize the semantic metric registry

Status: implemented locally for M18. This decision authorizes no M19 interface work, upload,
deployment, push, publication, or public row-data activation.

## Decision

Use tracked registry `metrics.v1` as the single source for 11 released analytical measures, 17
compatible dimensions, and three query contexts: portfolio, filing cohorts, and pending inventory.
The registry owns labels, definitions, tooltips, limitations, units, formats, export labels, context
compatibility, support rules, aggregate-cube mappings, and immutable dataset and schema compatibility.

Compile query SQL only from registered identifiers and eight fixed aggregation tokens. Requests may
select registered measures, compatible dimensions, allowlisted operators, deterministic selected-field
sorts, and a result limit no larger than 10,000. Filter values use bound parameters. Requests cannot
supply a relation, expression, aggregation, SQL fragment, or raw SQL.

Generate the deployment JSON and user-facing metric definitions from the TOML registry. Reconcile
registered formulas through exact numerator and denominator terms against every supported aggregate
cube slice. Treat equivalent floating-point display variation as diagnostic while requiring exact
count and summed-day inputs.

## Evidence

Registry coverage is 1.0. Eleven of 11 measures have complete presentation and export metadata, all 17
context bindings are present, and all 20 measure fields exposed by the three aggregate-cube collections
map exactly once. Seventeen dimensions carry types, labels, operators, definitions, tooltips, and
export labels.

Twelve generated queries reconcile 8,970 supported slices through 55,158 exact comparisons against
the private M16 mart and approved aggregate cube. Maximum exact difference is 0.0. Derived display
values differ by at most `4.547473508864641e-13` from equivalent aggregation order.

Focused tests cover registry completeness, canonical compiled artifacts, complete cube-field mapping,
grouping-set selection, context and operator rejection, parameter binding, support rules, result
bounds, and executable censoring formulas.

## Why

One semantic source prevents a chart, table, tooltip, export, and methodology page from assigning
different meaning or formulas to the same measure. Context bindings make shared measures reusable
without pretending every dimension or formula is valid everywhere. Fixed aggregation tokens keep the
tracked registry declarative and make generated SQL auditable.

Exact numerator and denominator comparison distinguishes real data drift from machine-epsilon changes
in derived averages. It also proves that pending shares, match coverage, observed duration, and pending
age use the same governed populations as the approved cube.

## Alternatives rejected

- Accept raw SQL from report state. Rejected because URL or user input must never cross the SQL trust
  boundary.
- Store arbitrary SQL expressions in the registry. Rejected because eight fixed aggregation tokens
  cover the released measures with a smaller review surface.
- Define formulas independently in React, worker code, exports, and documentation. Rejected because
  duplicated semantics drift.
- Treat cube aliases as separate measures. Rejected because support, observed, and censored aliases map
  to the same governed semantic measures.
- Compare floating-point display values bit-for-bit. Rejected because equivalent aggregation order can
  vary below presentation precision while exact sufficient statistics remain identical.

## Changed

- Added the versioned semantic registry and publication-contract compatibility checks.
- Added a fail-closed query compiler with bound filters, compatible dimensions, minimum support, safe
  sorting, and bounded results.
- Added canonical deployment JSON and generated user-facing metric definitions.
- Added full private M16 reconciliation and focused semantic-layer tests.

## Limitations

- M18 defines and verifies semantic contracts but does not integrate report pages or browser URL state.
- Minimum support governs analytical aggregates; M20 separately governs bounded record exploration.
- The display diagnostic is not the release equality boundary; exact sufficient statistics are.
- M21 and M22 retain runtime, accessibility, security, terms, live-origin, and publication gates.

## Not done

- No M19 report page, route, bookmark, synchronized filter, or visualization was built.
- No row data, private manifest, key, warehouse, or evidence file entered tracked Git.
- No upload, deployment, provider mutation, push, publication, visibility change, or paid action
  occurred.
