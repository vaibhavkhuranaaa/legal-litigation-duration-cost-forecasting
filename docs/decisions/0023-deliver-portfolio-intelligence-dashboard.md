# Deliver a full-population portfolio intelligence dashboard

Status: implemented for v1.1. Decision 0024 supersedes only the future aggregate-only limitation by
planning governed statistical-record drill-through. The current dashboard remains aggregate-only.

## Decision

Replace the split portfolio and matter-planner interface with one enterprise analytics workspace and a connected secondary scenario lab.

The dashboard uses one persistent analytical scope for executive measures, filing trends, district and case-family rankings, pending-inventory aging, observed cohort context, evidence status, methodology, and export. Pure selectors derive every view from the versioned full-population cube. Static Pages and the offline API continue to use the same artifact.

## Why

The previous interface emphasized unavailable predictions and presented the strongest analytical evidence as a long report. That made the product appear unable to act even though it supports substantial descriptive and diagnostic analysis across all 5,008,334 governed records.

An enterprise dashboard better matches the supported decision: understand where workload is concentrated, how pending inventory is aging, how historical cohorts differ, and how much evidence is available for each selected scope.

## Alternatives rejected

- Keep the planning-first name and layout. Rejected because the product has no validated duration model or observed cost data.
- Hide failed capabilities. Rejected because capability truth remains part of the release contract.
- Add more static charts without shared scope. Rejected because disconnected filters and panels do not form an analytical product.
- Publish matter-level drill-down. Rejected because public evidence remains aggregate-only.

## What was not done

- No duration, outcome, cost, staffing, or docket-event prediction was added.
- No private warehouse, dataset, model, or identifier was exposed.
- No publication threshold was weakened.
- No scenario output was relabeled as observed or recommended.

## Consequences

- The public product is positioned as portfolio intelligence rather than a duration planner.
- Analysts can move from a ranking into a synchronized scope and export the exact evidence shown.
- The scenario lab remains useful but clearly secondary and synthetic.
- Future analytics can extend pure selectors and panels without changing the governed cube or API boundary.
