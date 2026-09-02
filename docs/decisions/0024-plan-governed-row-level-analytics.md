# Plan governed row-level analytics on a static lakehouse

## Decision

Build the next analytical release as a zero-cost static lakehouse. Publish the complete 5,008,334-row
statistical population as a narrow, governed Parquet serving mart, query it in-browser through
DuckDB-WASM, and retain the existing aggregate cube as the executive fast path.

Keep GitHub Pages as the application host and treat it as one candidate data origin. M17 benchmarks a
representative partition locally and performs read-only capability probes against candidate public
origins. The final data origin remains provisional until an approved M22 candidate deployment verifies
the exact Parquet URLs. Keep a configurable data base URL so the same versioned files can move between
approved static origins without changing report semantics.
Deliver the work through M15 through M22 as specified in the
[row-level analytics release plan](../row-level-analytics-plan.md).

## Why

The current aggregate dashboard answers broad portfolio questions but cannot show the records behind a
measure or support flexible combinations beyond its precomputed cube. The source population is already
governed and compact enough for a browser-oriented analytical serving layer, provided that publication
uses a strict allowlist and ordinary queries do not download the whole dataset.

This architecture preserves the zero-dollar ceiling, avoids a continuously running backend, provides a
credible analytical engineering story, and supports Power BI-style filtering, cross-filtering,
drill-through, and a record explorer.

## Alternatives rejected

- Commit the row data to Git. Rejected because generated data does not belong in source history and
  repository file limits make that boundary fragile.
- Expose the private DuckDB warehouse. Rejected because it contains private lineage and operational
  evidence and is not a public serving contract.
- Use D1 as the primary analytical store. Rejected because analytical scans over the full population do
  not fit the free row-read model efficiently.
- Start with a continuously running API and database. Rejected because the current scope does not require
  server-side security or mutation and the operating ceiling is zero dollars.
- Publish unrestricted source rows. Rejected because public availability of a source does not eliminate
  the product's duty to minimize fields, preserve source semantics, and exclude unnecessary identifiers
  and text.

## What was not done

- No row-level dataset was generated, uploaded, deployed, or published by this decision.
- No duration, cost, event, outcome, or staffing prediction was authorized.
- No current aggregate publication rule was silently weakened.
- No external storage service or paid resource was provisioned.

## Consequences

- The current v1.1 dashboard remains aggregate-only until M22 passes and receives release approval.
- M15 freezes the public schema before a full dataset build.
- M17 benchmarks a single representative partition before M16 scales the row mart and records a
  provisional hosting policy without uploading public data.
- Report measures and documentation share one versioned semantic registry.
- Browser memory, transfer, query latency, cancellation, accessibility, and rollback become explicit
  release gates.
- A full-data download is deliberate and separate from ordinary report queries.
