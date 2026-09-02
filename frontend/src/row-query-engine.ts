import * as duckdb from "@duckdb/duckdb-wasm";
import duckdbEhWasm from "@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url";
import ehWorker from "@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url";
import duckdbMvpWasm from "@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url";
import mvpWorker from "@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url";

import {
  MAXIMUM_CSV_ROWS,
  MAXIMUM_QUERY_ROWS,
  compileRecordCount,
  compileRecordDetail,
  compileRecordQuery,
  normalizeRecordValue,
  recordsToCsv,
  type CompiledRecordQuery,
  type RecordQuerySpec,
  type RecordRow,
} from "./record-explorer";
import {
  checkedBaseUrl,
  validateManifest,
  validateManifestResponse,
  validatePartitionResponse,
  type RowManifest,
  type RowPartition,
} from "./row-origin-contract";

const BUNDLES: duckdb.DuckDBBundles = {
  mvp: { mainModule: duckdbMvpWasm, mainWorker: mvpWorker },
  eh: { mainModule: duckdbEhWasm, mainWorker: ehWorker },
};

export interface QueryTiming {
  name: string;
  durationMs: number;
  rows: number;
}

export type { RowManifest, RowPartition } from "./row-origin-contract";

export type RecordPage = {
  rows: RecordRow[];
  matchingRecords: number;
  durationMs: number;
  filingYear: number;
};

export type ExportResult = {
  blob: Blob;
  rows: number;
  columns: number;
};

function tableRows(
  table: Awaited<ReturnType<duckdb.AsyncDuckDBConnection["query"]>>,
): RecordRow[] {
  const columns = table.schema.fields.map((field) => field.name);
  return table.toArray().map((row) => Object.fromEntries(
    columns.map((column) => [column, normalizeRecordValue(row[column], column)]),
  ));
}

export class RowQueryEngine {
  private activeYear: number | null = null;
  private terminated = false;

  private constructor(
    private readonly db: duckdb.AsyncDuckDB,
    private readonly connection: duckdb.AsyncDuckDBConnection,
    private readonly baseUrl: URL,
    readonly manifest: RowManifest,
  ) {}

  static async create(dataBaseUrl: string): Promise<RowQueryEngine> {
    const baseUrl = checkedBaseUrl(dataBaseUrl);
    const manifestUrl = new URL("manifest.json", baseUrl);
    const response = await fetch(manifestUrl, { cache: "no-store", redirect: "error" });
    validateManifestResponse(response, manifestUrl);
    const manifest = validateManifest(await response.json());
    const bundle = await duckdb.selectBundle(BUNDLES);
    if (!bundle.mainWorker) throw new Error("No compatible DuckDB-WASM worker bundle");
    const worker = new Worker(bundle.mainWorker);
    const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
    await db.open({
      accessMode: duckdb.DuckDBAccessMode.AUTOMATIC,
      filesystem: { reliableHeadRequests: true, allowFullHTTPReads: false },
      query: { castBigIntToDouble: true, castTimestampToDate: true },
    });
    const connection = await db.connect();
    await connection.query("set memory_limit='256MB'");
    return new RowQueryEngine(db, connection, baseUrl, manifest);
  }

  get years(): number[] {
    return this.manifest.partitions.map((partition) => partition.filing_year).sort((left, right) => right - left);
  }

  partitionUrl(partition: RowPartition): string {
    return new URL(partition.path, this.baseUrl).toString();
  }

  manifestUrl(): string {
    return new URL("manifest.json", this.baseUrl).toString();
  }

  private async ensureYear(filingYear: number): Promise<void> {
    if (this.activeYear === filingYear) return;
    const partition = this.manifest.partitions.find((item) => item.filing_year === filingYear);
    if (!partition) throw new Error(`Filing year ${filingYear} is not in the row manifest`);
    const partitionUrl = new URL(partition.path, this.baseUrl);
    const response = await fetch(partitionUrl, {
      method: "HEAD",
      headers: { Range: "bytes=0-" },
      cache: "no-cache",
      redirect: "error",
    });
    validatePartitionResponse(response, partitionUrl, partition);
    const filename = `records-${filingYear}.parquet`;
    await this.connection.query("drop view if exists governed_records");
    await this.db.dropFiles();
    await this.db.registerFileURL(filename, partitionUrl.toString(), duckdb.DuckDBDataProtocol.HTTP, false);
    const registered = await this.db.globFiles(filename);
    if (registered.length !== 1 || registered[0]?.dataProtocol !== duckdb.DuckDBDataProtocol.HTTP) {
      throw new Error("DuckDB-WASM did not retain the HTTP partition registration");
    }
    await this.connection.query(`create view governed_records as select * from read_parquet('${filename}')`);
    this.activeYear = filingYear;
  }

  private async prepared(compiled: CompiledRecordQuery) {
    const statement = await this.connection.prepare(compiled.sql);
    try {
      return await statement.query(...compiled.parameters);
    } finally {
      await statement.close();
    }
  }

  async page(filingYear: number, spec: RecordQuerySpec): Promise<RecordPage> {
    const started = performance.now();
    await this.ensureYear(filingYear);
    const count = await this.prepared(compileRecordCount(spec));
    const page = await this.prepared(compileRecordQuery(spec));
    return {
      rows: tableRows(page),
      matchingRecords: Number(count.getChild("matching_records")?.get(0) ?? 0),
      durationMs: performance.now() - started,
      filingYear,
    };
  }

  async detail(filingYear: number, releaseRecordKey: string): Promise<RecordRow> {
    await this.ensureYear(filingYear);
    const rows = tableRows(await this.prepared(compileRecordDetail(releaseRecordKey)));
    if (rows.length !== 1) throw new Error("Record detail is unavailable in the active partition");
    return rows[0];
  }

  async csv(filingYear: number, spec: RecordQuerySpec): Promise<ExportResult> {
    await this.ensureYear(filingYear);
    const query = compileRecordQuery({ ...spec, limit: MAXIMUM_CSV_ROWS, offset: 0 }, MAXIMUM_CSV_ROWS);
    const rows = tableRows(await this.prepared(query));
    const csv = recordsToCsv(rows, spec.columns);
    return {
      blob: new Blob([csv], { type: "text/csv;charset=utf-8" }),
      rows: rows.length,
      columns: [...new Set(["release_record_key", ...spec.columns])].length,
    };
  }

  async parquet(filingYear: number, spec: RecordQuerySpec): Promise<ExportResult> {
    await this.ensureYear(filingYear);
    const query = compileRecordQuery({ ...spec, limit: MAXIMUM_QUERY_ROWS, offset: 0 });
    const output = "m20-filtered.parquet";
    await this.connection.query("drop table if exists m20_filtered_export");
    const statement = await this.connection.prepare(`create temp table m20_filtered_export as ${query.sql}`);
    try {
      await statement.query(...query.parameters);
    } finally {
      await statement.close();
    }
    const count = await this.connection.query("select count(*)::integer as exported_records from m20_filtered_export");
    const rows = Number(count.getChild("exported_records")?.get(0) ?? 0);
    await this.db.dropFile(output).catch(() => undefined);
    try {
      await this.connection.query(`copy m20_filtered_export to '${output}' (format parquet, compression zstd)`);
      const verified = await this.connection.query(`select count(*)::integer as exported_records from read_parquet('${output}')`);
      if (Number(verified.getChild("exported_records")?.get(0) ?? -1) !== rows) {
        throw new Error("Filtered Parquet row count did not reconcile");
      }
      const schema = await this.connection.query(`select * from read_parquet('${output}') limit 0`);
      const expectedColumns = [...new Set(["release_record_key", ...spec.columns])];
      if (schema.schema.fields.map((field) => field.name).join("|") !== expectedColumns.join("|")) {
        throw new Error("Filtered Parquet projected columns did not reconcile");
      }
      const bytes = await this.db.copyFileToBuffer(output);
      if (bytes.byteLength < 8) throw new Error("Filtered Parquet output is empty");
      return {
        blob: new Blob([bytes.slice().buffer], { type: "application/vnd.apache.parquet" }),
        rows,
        columns: [...new Set(["release_record_key", ...spec.columns])].length,
      };
    } finally {
      await this.db.dropFile(output).catch(() => undefined);
      await this.connection.query("drop table if exists m20_filtered_export");
    }
  }

  async query(name: string, sql: string, filingYear = 2025): Promise<QueryTiming> {
    const started = performance.now();
    await this.ensureYear(filingYear);
    const result = await this.connection.query(sql);
    return { name, durationMs: performance.now() - started, rows: result.numRows };
  }

  async cancelByTerminatingWorker(sql: string, delayMs = 50, filingYear = 2025): Promise<number> {
    await this.ensureYear(filingYear);
    void this.connection.query(sql).catch(() => undefined);
    await new Promise((resolve) => window.setTimeout(resolve, delayMs));
    const started = performance.now();
    await this.terminate();
    return performance.now() - started;
  }

  async terminate(): Promise<void> {
    if (this.terminated) return;
    this.terminated = true;
    await this.db.terminate();
  }

  async close(): Promise<void> {
    if (this.terminated) return;
    try {
      await this.connection.close();
    } finally {
      await this.terminate();
    }
  }
}
