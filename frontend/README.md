# Product interface

React, TypeScript, Vite, and ECharts implement the full-population portfolio intelligence dashboard and its separate synthetic scenario workspace. GitHub Pages consumes the versioned aggregate cube directly; the offline container serves the same cube through the typed local API. Neither mode requires a warehouse connection or publishes matter-level rows.

The next release keeps that cube as the initial render and fallback, then adds a DuckDB-WASM Web
Worker for projected, filtered scans of versioned remote Parquet partitions. The worker will return
bounded Arrow batches to charts and a virtualized record table. A manifest and semantic metric
registry will keep data, queries, labels, exports, and methodology compatible. This architecture is
documented in the [row-level analytics release plan](../docs/row-level-analytics-plan.md); it is not
part of the current live release.
