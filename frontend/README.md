# Product interface

React, TypeScript, Vite, and ECharts implement the full-population portfolio intelligence workspace.
The local row-release continuation adds eight responsive report destinations, one URL-backed analytical scope,
active chips, cross-filtering, drill breadcrumbs, browser-local bookmarks, explicit recovery states,
and a bounded Record Explorer over the production row-data origin.
GitHub Pages consumes the versioned aggregate cube and immutable row-data manifest; the offline
container serves the aggregate cube through the typed local API. Neither mode requires a warehouse
connection or publishes source identifiers.

The cube remains the initial render and fallback. `VITE_ROW_DATA_BASE_URL` activates a compatible
manifest and annual Parquet origin. DuckDB-WASM loads one annual partition, compiles allowlisted and
parameterized queries, returns 200-row pages to a virtualized table, and supports projected columns,
stable sorting, pinning, resizing, opaque-key detail, formula-safe bounded CSV, read-back-verified
filtered Parquet, a deterministic provenance sidecar for each successful bounded export, and an
explicit complete-data path. M21 validates the complete manifest and every partition response,
requires exact range and immutable-cache behavior, caps DuckDB at 256 MB, and replaces the worker after
cancel or timeout while preserving selected scope. Without a valid origin the explorer fails closed
and keeps aggregate scope available. See the
[row-level analytics release plan](../docs/row-level-analytics-plan.md). M22 packages
the application, generated allowlist-only dictionary, semantic registry, manifest, and annual
partitions into a deterministic inventory. The production Worker serves only those immutable,
allowlisted row-data paths.
