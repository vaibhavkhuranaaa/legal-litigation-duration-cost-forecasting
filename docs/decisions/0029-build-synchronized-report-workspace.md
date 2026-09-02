# Build the synchronized report workspace

Status: implemented locally for M19. This decision authorizes no M20 row explorer or export work,
upload, deployment, push, publication, provider mutation, or public row-data activation.

## Decision

Extend the established governed portfolio cockpit into eight report destinations over the approved
aggregate cube: Executive Overview, Filing Trends, Pending Inventory and Aging, Case Mix, District
Comparison, Record Explorer, Data Quality and Coverage, and Scenario Lab and Methods.

Use one typed report state for the current page, district, nature family, historical-cohort context,
ranking mode, and drill origin. Serialize every non-default field into a canonical query string.
Browser navigation restores that state; bookmarks store only the relative report URL and a descriptive
label in local storage. District and nature selections update the shared scope, active chips, dependent
reports, and URL. Cross-filter actions that change destination retain a drill breadcrumb.

Keep the approved aggregate cube as the initial render and rollback path. Present loading, cancellation,
request error, empty, support-withheld, and capability-refusal states explicitly. The Record Explorer
page must preserve scope and show an aggregate preview while refusing rows, columns, and exports until
M20 implements and verifies those capabilities.

## Evidence

All eight destinations render at the 1,440 by 900 desktop and 390 by 844 mobile reference profiles.
The mobile shell exposes its five secondary reports through a named More control and keeps filters
behind a named Filters disclosure.

Twenty deterministic browser scenarios pass: eight report routes; shared filter application and
cross-page persistence; clear; district cross-filter and drill-through; breadcrumb context; URL reload
round-trip; bookmark save and restore; empty-state recovery; request-error retry; cancellation with
preserved URL state and retry; mobile More navigation; and mobile filter disclosure. Four pure state
tests separately verify the eight-page declaration, complete URL-state round-trip, incompatible-value
normalization, and default-state canonicalization.

The production Pages build succeeds, retains the embedded design contract, and continues to load the
1.8 MB aggregate cube directly. Automated accessibility inspection reports zero violations; ECharts
SVG text remains an incomplete manual contrast determination because the scanner cannot infer its
rendered background.

## Why

A single report state prevents filters, drill targets, bookmarks, and browser history from disagreeing.
Relative URL bookmarks are portable across the local root and the configured Pages base path. Keeping
district and nature family as the synchronized aggregate slicers avoids implying that dimensions only
available in the future row engine already affect every aggregate measure.

An explicit Record Explorer refusal preserves the eight-page information architecture without
silently starting M20. Users can see the selected population and publication boundary while row
transfer and export remain zero.

## Alternatives rejected

- Add eight independent dashboards with local filters. Rejected because the same scope could display
  different evidence on different pages.
- Put report state in component memory only. Rejected because reload, browser navigation, and review
  handoffs would not reproduce an analytical view.
- Store bookmark copies of results. Rejected because URLs are sufficient and avoid duplicating data.
- Add the M20 table and disable only export. Rejected because virtualization, bounded queries, column
  controls, and exports are one separately verified capability boundary.
- Claim all 17 registered dimensions are aggregate-fast-path slicers. Rejected because the approved
  cube reconciles only district, nature family, filing year, and age band in their compatible contexts.

## Changed

- Added typed report-page and URL-state contracts with focused tests.
- Added the eight-destination responsive report shell, synchronized filters, chips, cross-filtering,
  drill breadcrumbs, browser history, and local bookmarks.
- Added report-specific aggregate views, registered metric definitions, and synthetic scenario methods.
- Added explicit loading, cancellation, error, empty, and Record Explorer refusal recovery paths.
- Updated interface, architecture, release-plan, and frontend documentation for the completed local M19
  boundary.

## Limitations

- District and nature family are the shared aggregate-fast-path slicers. The row-engine dimensions in
  the registered semantic contract become interactive only after their data source is available.
- Browser bookmarks are local to one browser profile; they are not synchronized to an account.
- Automated interaction tests do not replace stakeholder usability, keyboard, and screen-reader review.
- M21 retains complete cross-browser, accessibility, performance, memory, security, and reliability
  gates.

## Not done

- No virtualized row table, row query, column picker, pinning, detail drawer, CSV, Parquet, or complete
  dataset download was implemented.
- No private mart, manifest, opaque key, dataset, warehouse, screenshot, or evidence record entered
  tracked Git.
- No upload, deployment, provider mutation, push, publication, visibility change, or paid action
  occurred.
