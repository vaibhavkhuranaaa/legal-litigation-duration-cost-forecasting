import { useEffect, useMemo, useRef, useState } from "react";

import {
  INTERACTIVE_ROW_LIMIT,
  defaultRecordColumns,
  recordExportProvenance,
  recordColumns,
  type RecordQuerySpec,
  type RecordRow,
  type RecordValue,
  type SortDirection,
} from "./record-explorer";
import { RowQueryEngine, type ExportResult, type RecordPage } from "./row-query-engine";

const integer = new Intl.NumberFormat("en-US");
const bytes = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const rowHeight = 38;
const viewportRows = 11;
const overscan = 4;
const queryTimeoutMs = 10_000;

type RecordExplorerProps = {
  districtCode: string;
  natureFamily: string;
  aggregateRecords: number;
  onClearScope: () => void;
};

type LoadState = "loading" | "ready" | "error" | "unconfigured";

function displayValue(value: RecordValue): string {
  if (value === null) return "Not applicable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return integer.format(value);
  return value;
}

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function exportName(year: number, districtCode: string, natureFamily: string, extension: string) {
  const district = districtCode === "all" ? "all-districts" : `district-${districtCode.toLowerCase()}`;
  const nature = natureFamily === "all" ? "all-families" : natureFamily;
  return `fjc-civil-${year}-${district}-${nature}.${extension}`;
}

export function RecordExplorer({ districtCode, natureFamily, aggregateRecords, onClearScope }: RecordExplorerProps) {
  const dataBaseUrl = (import.meta.env.VITE_ROW_DATA_BASE_URL as string | undefined)?.trim() ?? "";
  const [retryToken, setRetryToken] = useState(0);
  const [loadState, setLoadState] = useState<LoadState>(dataBaseUrl ? "loading" : "unconfigured");
  const [loadError, setLoadError] = useState("");
  const [engine, setEngine] = useState<RowQueryEngine | null>(null);
  const [year, setYear] = useState(2025);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(defaultRecordColumns);
  const [sortColumn, setSortColumn] = useState("filed_month");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [pinnedColumn, setPinnedColumn] = useState("release_record_key");
  const [resizedColumn, setResizedColumn] = useState("release_record_key");
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(() => Object.fromEntries(recordColumns.map((column) => [column.id, column.width])));
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<RecordPage | null>(null);
  const [queryState, setQueryState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [queryError, setQueryError] = useState("");
  const [recoveryMessage, setRecoveryMessage] = useState("");
  const [queryRetry, setQueryRetry] = useState(0);
  const [selected, setSelected] = useState<RecordRow | null>(null);
  const [detailState, setDetailState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [scrollTop, setScrollTop] = useState(0);
  const [exporting, setExporting] = useState<"csv" | "parquet" | null>(null);
  const [exportMessage, setExportMessage] = useState("");
  const [provenanceDownload, setProvenanceDownload] = useState<{ blob: Blob; filename: string } | null>(null);
  const [downloadTermsAccepted, setDownloadTermsAccepted] = useState(false);
  const querySequence = useRef(0);
  const detailRef = useRef<HTMLElement | null>(null);
  const detailTriggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!dataBaseUrl) {
      setLoadState("unconfigured");
      return;
    }
    let active = true;
    let instance: RowQueryEngine | null = null;
    setLoadState("loading");
    setLoadError("");
    void RowQueryEngine.create(dataBaseUrl).then((created) => {
      instance = created;
      if (!active) return created.close();
      const latestComplete = created.years.find((value) => value < Number(created.manifest.source_snapshot_cutoff.slice(0, 4)));
      setYear((current) => created.years.includes(current) ? current : latestComplete ?? created.years[0] ?? 2025);
      setEngine(created);
      setLoadState("ready");
    }).catch((reason) => {
      if (!active) return;
      setLoadError(reason instanceof Error ? reason.message : "Row engine initialization failed");
      setLoadState("error");
    });
    return () => {
      active = false;
      if (instance) void instance.close();
      setEngine(null);
    };
  }, [dataBaseUrl, retryToken]);

  useEffect(() => {
    setOffset(0);
    setSelected(null);
  }, [districtCode, natureFamily, year, sortColumn, sortDirection, visibleColumns]);

  const spec = useMemo<RecordQuerySpec>(() => ({
    columns: visibleColumns,
    districtCode,
    natureFamily,
    sortColumn,
    sortDirection,
    limit: INTERACTIVE_ROW_LIMIT,
    offset,
  }), [districtCode, natureFamily, offset, sortColumn, sortDirection, visibleColumns]);

  useEffect(() => {
    if (!engine || loadState !== "ready") return;
    const sequence = ++querySequence.current;
    setQueryState("loading");
    setQueryError("");
    const timeout = window.setTimeout(() => {
      if (sequence !== querySequence.current) return;
      querySequence.current += 1;
      setRecoveryMessage("The query exceeded 10 seconds. Its worker was stopped and replaced automatically.");
      setQueryState("idle");
      setEngine(null);
      void engine.terminate().finally(() => setRetryToken((value) => value + 1));
    }, queryTimeoutMs);
    void engine.page(year, spec).then((result) => {
      if (sequence !== querySequence.current) return;
      window.clearTimeout(timeout);
      setPage(result);
      setScrollTop(0);
      setQueryState("ready");
    }).catch((reason) => {
      if (sequence !== querySequence.current) return;
      window.clearTimeout(timeout);
      setQueryError(reason instanceof Error ? reason.message : "Row query failed");
      setQueryState("error");
    });
    return () => window.clearTimeout(timeout);
  }, [engine, loadState, queryRetry, spec, year]);

  useEffect(() => {
    if (selected) detailRef.current?.focus();
  }, [selected]);

  const columns = visibleColumns.map((id) => recordColumns.find((column) => column.id === id)).filter((column) => column !== undefined);
  const firstVisible = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const lastVisible = Math.min(page?.rows.length ?? 0, firstVisible + viewportRows + overscan * 2);
  const visibleRows = page?.rows.slice(firstVisible, lastVisible) ?? [];
  const totalPages = page ? Math.max(1, Math.ceil(page.matchingRecords / INTERACTIVE_ROW_LIMIT)) : 1;
  const currentPage = Math.floor(offset / INTERACTIVE_ROW_LIMIT) + 1;

  function toggleColumn(column: string) {
    if (column === "release_record_key") return;
    setVisibleColumns((current) => current.includes(column)
      ? current.length > 2 ? current.filter((item) => item !== column) : current
      : [...current, column]);
    if (pinnedColumn === column) setPinnedColumn("release_record_key");
  }

  function changeSort(column: string) {
    if (sortColumn === column) setSortDirection((current) => current === "asc" ? "desc" : "asc");
    else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  }

  async function inspectRecord(row: RecordRow) {
    if (!engine) return;
    setSelected(row);
    setDetailState("loading");
    try {
      setSelected(await engine.detail(year, String(row.release_record_key)));
      setDetailState("ready");
    } catch {
      setDetailState("error");
    }
  }

  function cancelQuery() {
    if (!engine || queryState !== "loading") return;
    querySequence.current += 1;
    setRecoveryMessage("The query was cancelled. Its worker was stopped and replaced automatically.");
    setQueryState("idle");
    setEngine(null);
    void engine.terminate().finally(() => setRetryToken((value) => value + 1));
  }

  function closeDetail() {
    setSelected(null);
    window.requestAnimationFrame(() => detailTriggerRef.current?.focus());
  }

  async function runExport(format: "csv" | "parquet") {
    if (!engine) return;
    setExporting(format);
    setExportMessage("");
    setProvenanceDownload(null);
    try {
      const result: ExportResult = format === "csv" ? await engine.csv(year, spec) : await engine.parquet(year, spec);
      const filename = exportName(year, districtCode, natureFamily, format);
      download(result.blob, filename);
      const provenance = recordExportProvenance(engine.manifest, spec, year, format, result.rows);
      setProvenanceDownload({
        blob: new Blob([`${JSON.stringify(provenance, null, 2)}\n`], { type: "application/json" }),
        filename: `${filename}.provenance.json`,
      });
      setExportMessage(`${format.toUpperCase()} prepared: ${integer.format(result.rows)} rows and ${result.columns} projected columns.`);
    } catch (reason) {
      setExportMessage(`${format.toUpperCase()} refused: ${reason instanceof Error ? reason.message : "export failed closed"}.`);
    } finally {
      setExporting(null);
    }
  }

  if (loadState === "unconfigured") return <section className="bounded-state refusal-state record-origin-state" role="status">
    <h2>Governed row origin is not configured</h2>
    <p>Aggregate context remains available. The row-data origin is absent or incompatible; public row assets stay disabled until release approval and live-origin verification.</p>
    <button className="button-secondary" type="button" onClick={onClearScope}>Clear analytical scope</button>
  </section>;

  if (loadState === "loading") return <section className="record-loading" aria-live="polite">
    <div><strong>Starting governed row engine</strong><span>Validating manifest, WebAssembly runtime, and annual partition policy.</span></div>
    <span className="loading-block" />
  </section>;

  if (loadState === "error") return <section className="bounded-state fatal-state record-origin-state" role="alert">
    <h2>Row engine did not start</h2><p>{loadError}. Aggregate context and URL state remain intact.</p>
    <button className="button-primary" type="button" onClick={() => setRetryToken((value) => value + 1)}>Retry row engine</button>
  </section>;

  return <div className="record-explorer-layout">
    <section className="record-command-bar" aria-label="Record query controls">
      <div className="record-scope-summary"><strong>{integer.format(aggregateRecords)} records</strong><span>aggregate scope / all filing years</span></div>
      <label>Filing-year partition<select data-testid="record-year" value={year} onChange={(event) => setYear(Number(event.target.value))}>{engine?.years.map((value) => <option value={value} key={value}>{value}{value === 2026 ? " · partial" : ""}</option>)}</select></label>
      <details className="column-picker"><summary>Columns ({visibleColumns.length}/{recordColumns.length})</summary><div>{recordColumns.map((column) => <label key={column.id}><input type="checkbox" checked={visibleColumns.includes(column.id)} disabled={column.id === "release_record_key"} onChange={() => toggleColumn(column.id)} />{column.label}</label>)}</div></details>
      <label>Pin column<select value={pinnedColumn} onChange={(event) => setPinnedColumn(event.target.value)}>{columns.map((column) => <option value={column.id} key={column.id}>{column.label}</option>)}</select></label>
      <label>Resize column<select value={resizedColumn} onChange={(event) => setResizedColumn(event.target.value)}>{columns.map((column) => <option value={column.id} key={column.id}>{column.label}</option>)}</select></label>
      <label className="column-width">Width<input type="range" min="80" max="260" step="4" value={columnWidths[resizedColumn]} onInput={(event) => { const width = Number(event.currentTarget.value); setColumnWidths((current) => ({ ...current, [resizedColumn]: width })); }} /><span>{columnWidths[resizedColumn]}px</span></label>
    </section>

    <section className="record-query-status" aria-live="polite" aria-busy={queryState === "loading"}>
      <div><strong>{queryState === "ready" ? `${integer.format(page?.matchingRecords ?? 0)} matching ${year} records` : queryState === "loading" ? "Querying one annual partition" : "Record query needs attention"}</strong><span>{queryState === "ready" ? recoveryMessage || `${page?.rows.length ?? 0} rows loaded in ${Math.round(page?.durationMs ?? 0)} ms / limit ${INTERACTIVE_ROW_LIMIT}` : "Only allowlisted projected columns and bounded parameters are accepted."}</span></div>
      {queryState === "loading" && <button className="button-secondary" type="button" onClick={cancelQuery}>Cancel query</button>}
      {queryState === "error" && <button className="button-secondary" type="button" onClick={() => setQueryRetry((value) => value + 1)}>Retry query</button>}
    </section>

    {queryState === "error" ? <section className="bounded-state fatal-state record-query-error" role="alert"><h2>Bounded row query failed</h2><p>{queryError}. Change the partition or retry; no fallback query will scan the complete dataset.</p></section> :
      queryState === "ready" && page?.matchingRecords === 0 ? <section className="bounded-state empty-state record-query-error" role="status"><h2>No governed rows match this year and scope</h2><p>Choose another filing-year partition or broaden the shared district and case-family filters.</p><button className="button-secondary" type="button" onClick={onClearScope}>Clear analytical scope</button></section> :
      <section className={`record-data-grid${selected ? " detail-open" : ""}`}>
        <div className="record-table-panel">
          <div className="record-pager"><span>Page {integer.format(currentPage)} of {integer.format(totalPages)}</span><div><button type="button" disabled={offset === 0 || queryState !== "ready"} onClick={() => setOffset((value) => Math.max(0, value - INTERACTIVE_ROW_LIMIT))}>Previous {INTERACTIVE_ROW_LIMIT}</button><button type="button" disabled={!page || offset + INTERACTIVE_ROW_LIMIT >= page.matchingRecords || queryState !== "ready"} onClick={() => setOffset((value) => value + INTERACTIVE_ROW_LIMIT)}>Next {INTERACTIVE_ROW_LIMIT}</button></div></div>
          <div className="virtual-table-wrap" data-testid="record-viewport" tabIndex={0} aria-label="Virtualized record rows" onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}>
            <table className="record-table" style={{ minWidth: columns.reduce((sum, column) => sum + columnWidths[column.id], 0) }}>
              <caption className="visually-hidden">Governed statistical records for filing year {year}</caption>
              <thead><tr>{columns.map((column) => <th scope="col" aria-sort={sortColumn === column.id ? sortDirection === "asc" ? "ascending" : "descending" : "none"} key={column.id} className={pinnedColumn === column.id ? "pinned-column" : ""} style={{ width: columnWidths[column.id], minWidth: columnWidths[column.id] }}><button type="button" aria-label={`${column.label}, ${sortColumn === column.id ? `sorted ${sortDirection}ending` : "not sorted"}`} onClick={() => changeSort(column.id)}><span>{column.label}</span>{sortColumn === column.id && <i className={`sort-indicator ${sortDirection}`} aria-hidden="true" />}</button></th>)}</tr></thead>
              <tbody>{firstVisible > 0 && <tr className="virtual-spacer" aria-hidden="true"><td colSpan={columns.length} style={{ height: firstVisible * rowHeight }} /></tr>}{visibleRows.map((row) => <tr key={String(row.release_record_key)} className={selected?.release_record_key === row.release_record_key ? "selected-row" : ""}>{columns.map((column) => <td key={column.id} className={pinnedColumn === column.id ? "pinned-column" : ""} style={{ width: columnWidths[column.id], minWidth: columnWidths[column.id] }}>{column.id === "release_record_key" ? <button className="record-key-button" type="button" aria-controls="record-detail" aria-expanded={selected?.release_record_key === row.release_record_key} onClick={(event) => { detailTriggerRef.current = event.currentTarget; void inspectRecord(row); }} aria-label={`Inspect record ${row.release_record_key}`}>{String(row.release_record_key).slice(0, 14)}…</button> : displayValue(row[column.id] ?? null)}</td>)}</tr>)}{page && lastVisible < page.rows.length && <tr className="virtual-spacer" aria-hidden="true"><td colSpan={columns.length} style={{ height: (page.rows.length - lastVisible) * rowHeight }} /></tr>}</tbody>
            </table>
          </div>
        </div>
        {selected && <aside id="record-detail" ref={detailRef} tabIndex={-1} className="record-detail" aria-labelledby="record-detail-title">
          <div className="panel-heading"><div><h2 id="record-detail-title">Record detail</h2><p>Approved fields only. Statistical record does not guarantee a unique case.</p></div>{selected && <button className="text-action" type="button" onClick={closeDetail}>Close detail</button>}</div>
          {detailState === "loading" ? <div className="detail-empty"><strong>Loading approved fields</strong><p>One bounded key lookup stays inside the active annual partition.</p></div> : detailState === "error" ? <div className="detail-empty"><strong>Record detail unavailable</strong><p>The key lookup failed closed. Select the record again to retry.</p></div> : <dl>{recordColumns.map((column) => <div key={column.id}><dt>{column.label}</dt><dd>{displayValue(selected[column.id] ?? null)}</dd></div>)}</dl>}
        </aside>}
      </section>}

    <section className="record-export-band" aria-labelledby="record-export-title">
      <div><h2 id="record-export-title">Governed exports</h2><p>Current filing year, shared filters, deterministic sort, and selected columns. CSV stops at 50,000 rows; filtered Parquet stops at 10,000 and refuses on writer failure.</p></div>
      <div className="record-export-actions"><button className="button-primary" type="button" disabled={Boolean(exporting) || queryState !== "ready" || !page?.matchingRecords} onClick={() => void runExport("csv")}>{exporting === "csv" ? "Preparing CSV" : "Export bounded CSV"}</button><button className="button-secondary" type="button" disabled={Boolean(exporting) || queryState !== "ready" || !page?.matchingRecords} onClick={() => void runExport("parquet")}>{exporting === "parquet" ? "Preparing Parquet" : "Export filtered Parquet"}</button></div>
      {exportMessage && <div className="export-message" role="status"><p>{exportMessage}</p>{provenanceDownload && <button className="text-action" type="button" onClick={() => download(provenanceDownload.blob, provenanceDownload.filename)}>Download provenance JSON</button>}</div>}
    </section>

    <details className="complete-download">
      <summary>Complete dataset download</summary>
      <div><p>{integer.format(engine?.manifest.total_records ?? 0)} governed statistical records across {engine?.manifest.partitions.length ?? 0} immutable annual files ({bytes.format((engine?.manifest.partitions.reduce((sum, partition) => sum + partition.byte_size, 0) ?? 0) / 1_048_576)} MiB). This path is separate from interactive queries and is not enabled without an approved row origin.</p><p>{engine?.manifest.dataset_terms}</p><label><input type="checkbox" checked={downloadTermsAccepted} onChange={(event) => setDownloadTermsAccepted(event.target.checked)} />I understand the dataset terms and will preserve attribution.</label>{downloadTermsAccepted && <div className="download-links"><a href={engine?.manifestUrl()} target="_blank" rel="noreferrer">Manifest and integrity metadata</a>{engine?.manifest.partitions.map((partition) => <a key={partition.path} href={engine.partitionUrl(partition)} download>{partition.filing_year} partition / {integer.format(partition.row_count)} rows / {bytes.format(partition.byte_size / 1_048_576)} MiB</a>)}</div>}</div>
    </details>
  </div>;
}
