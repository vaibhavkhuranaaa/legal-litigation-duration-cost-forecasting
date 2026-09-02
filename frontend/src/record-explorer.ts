export const INTERACTIVE_ROW_LIMIT = 200;
export const MAXIMUM_QUERY_ROWS = 10_000;
export const MAXIMUM_CSV_ROWS = 50_000;

export type RecordValue = string | number | boolean | null;
export type RecordRow = Record<string, RecordValue>;
export type SortDirection = "asc" | "desc";

export type RecordColumn = {
  id: string;
  label: string;
  format: "text" | "integer" | "boolean" | "date";
  width: number;
  defaultVisible: boolean;
};

export const recordColumns: readonly RecordColumn[] = [
  { id: "release_record_key", label: "Record key", format: "text", width: 188, defaultVisible: true },
  { id: "circuit_code", label: "Circuit", format: "text", width: 82, defaultVisible: false },
  { id: "district_code", label: "District", format: "text", width: 92, defaultVisible: true },
  { id: "filed_month", label: "Filed month", format: "date", width: 116, defaultVisible: true },
  { id: "terminated_month", label: "Terminated month", format: "date", width: 136, defaultVisible: false },
  { id: "pending_status", label: "Pending", format: "boolean", width: 90, defaultVisible: true },
  { id: "event_observed", label: "Termination observed", format: "boolean", width: 148, defaultVisible: false },
  { id: "duration_days", label: "Elapsed days", format: "integer", width: 112, defaultVisible: true },
  { id: "nature_of_suit_code", label: "Nature code", format: "text", width: 108, defaultVisible: false },
  { id: "nature_of_suit_family", label: "Case family", format: "text", width: 172, defaultVisible: true },
  { id: "nature_of_suit_mapping_status", label: "Mapping status", format: "text", width: 130, defaultVisible: false },
  { id: "jurisdiction_code", label: "Jurisdiction", format: "text", width: 108, defaultVisible: false },
  { id: "origin_code", label: "Origin", format: "text", width: 92, defaultVisible: false },
  { id: "procedural_cohort", label: "Procedural cohort", format: "text", width: 178, defaultVisible: true },
  { id: "identity_quality_status", label: "Identity quality", format: "text", width: 132, defaultVisible: true },
  { id: "source_record_count", label: "Source records", format: "integer", width: 118, defaultVisible: false },
  { id: "recap_match_available", label: "RECAP match", format: "boolean", width: 112, defaultVisible: false },
  { id: "source_snapshot_cutoff", label: "Source cutoff", format: "date", width: 120, defaultVisible: false },
  { id: "dataset_version", label: "Dataset version", format: "text", width: 196, defaultVisible: false },
] as const;

export const defaultRecordColumns = recordColumns.filter((column) => column.defaultVisible).map((column) => column.id);

const columnIds = new Set(recordColumns.map((column) => column.id));

export type RecordQuerySpec = {
  columns: string[];
  districtCode: string;
  natureFamily: string;
  sortColumn: string;
  sortDirection: SortDirection;
  limit: number;
  offset: number;
};

export type CompiledRecordQuery = {
  sql: string;
  parameters: Array<string | number>;
};

export type RecordExportProvenance = {
  contract_id: string;
  dataset_version: string;
  schema_version: string;
  metric_registry_version: string;
  source_snapshot_cutoff: string;
  source_attribution: string;
  courtlistener_attribution: string;
  dataset_terms: string;
  filing_year: number;
  district_code: string;
  nature_of_suit_family: string;
  sort_column: string;
  sort_direction: SortDirection;
  projected_columns: string[];
  exported_rows: number;
  row_limit: number;
  format: "csv" | "parquet";
};

function quotedColumn(column: string): string {
  if (!columnIds.has(column)) throw new Error(`Unsupported record column: ${column}`);
  return `"${column}"`;
}

function boundedInteger(value: number, minimum: number, maximum: number, name: string): number {
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
    throw new Error(`${name} must be an integer from ${minimum} through ${maximum}`);
  }
  return value;
}

function whereClause(spec: RecordQuerySpec): { sql: string; parameters: string[] } {
  const predicates: string[] = [];
  const parameters: string[] = [];
  if (spec.districtCode !== "all") {
    predicates.push('"district_code" = ?');
    parameters.push(spec.districtCode);
  }
  if (spec.natureFamily !== "all") {
    predicates.push('"nature_of_suit_family" = ?');
    parameters.push(spec.natureFamily);
  }
  return { sql: predicates.length ? ` where ${predicates.join(" and ")}` : "", parameters };
}

export function compileRecordQuery(spec: RecordQuerySpec, maximumRows = MAXIMUM_QUERY_ROWS): CompiledRecordQuery {
  const limit = boundedInteger(spec.limit, 1, maximumRows, "limit");
  const offset = boundedInteger(spec.offset, 0, 5_008_333, "offset");
  if (spec.sortDirection !== "asc" && spec.sortDirection !== "desc") throw new Error("Unsupported sort direction");
  const requested = [...new Set(["release_record_key", ...spec.columns])];
  if (requested.length < 2) throw new Error("At least one analytical column is required");
  const projection = requested.map(quotedColumn).join(", ");
  const sort = quotedColumn(spec.sortColumn);
  const tieBreak = spec.sortColumn === "release_record_key" ? "" : ', "release_record_key" asc';
  const where = whereClause(spec);
  return {
    sql: `select ${projection} from governed_records${where.sql} order by ${sort} ${spec.sortDirection}${tieBreak} limit ? offset ?`,
    parameters: [...where.parameters, limit, offset],
  };
}

export function compileRecordCount(spec: RecordQuerySpec): CompiledRecordQuery {
  const where = whereClause(spec);
  return {
    sql: `select count(*)::integer as matching_records from governed_records${where.sql}`,
    parameters: where.parameters,
  };
}

export function compileRecordDetail(releaseRecordKey: string): CompiledRecordQuery {
  if (!/^[A-Za-z0-9_-]{22}$/.test(releaseRecordKey)) throw new Error("Record key is incompatible");
  return {
    sql: `select ${recordColumns.map((column) => quotedColumn(column.id)).join(", ")} from governed_records where "release_record_key" = ? limit 1`,
    parameters: [releaseRecordKey],
  };
}

export function normalizeRecordValue(value: unknown, column = ""): RecordValue {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === "number" && ["filed_month", "terminated_month", "source_snapshot_cutoff"].includes(column)) {
    return new Date(value).toISOString().slice(0, 10);
  }
  if (typeof value === "bigint") return Number(value);
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return value;
  return String(value);
}

export function formulaSafeValue(value: RecordValue): string {
  if (value === null) return "";
  const text = String(value);
  return /^[\t\r\n ]*[=+\-@]/.test(text) ? `'${text}` : text;
}

function csvCell(value: RecordValue): string {
  const safe = formulaSafeValue(value);
  return /[",\r\n]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
}

export function recordsToCsv(rows: RecordRow[], columns: string[]): string {
  const projection = [...new Set(["release_record_key", ...columns])];
  projection.forEach(quotedColumn);
  return [
    projection.map(csvCell).join(","),
    ...rows.map((row) => projection.map((column) => csvCell(row[column] ?? null)).join(",")),
  ].join("\r\n") + "\r\n";
}

export function recordExportProvenance(
  manifest: Pick<RecordExportProvenance,
    | "contract_id"
    | "dataset_version"
    | "schema_version"
    | "metric_registry_version"
    | "source_snapshot_cutoff"
    | "source_attribution"
    | "courtlistener_attribution"
    | "dataset_terms">,
  spec: RecordQuerySpec,
  filingYear: number,
  format: "csv" | "parquet",
  exportedRows: number,
): RecordExportProvenance {
  return {
    ...manifest,
    filing_year: filingYear,
    district_code: spec.districtCode,
    nature_of_suit_family: spec.natureFamily,
    sort_column: spec.sortColumn,
    sort_direction: spec.sortDirection,
    projected_columns: [...new Set(["release_record_key", ...spec.columns])],
    exported_rows: exportedRows,
    row_limit: format === "csv" ? MAXIMUM_CSV_ROWS : MAXIMUM_QUERY_ROWS,
    format,
  };
}
