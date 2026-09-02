import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/ibm-plex-sans/latin-700.css";

import { RowQueryEngine, type QueryTiming } from "./row-query-engine";
import "./m17.css";

declare global {
  interface Window {
    __consoleErrors: string[];
    __m17Result?: BenchmarkResult;
  }

  interface Performance {
    memory?: { usedJSHeapSize: number; totalJSHeapSize: number; jsHeapSizeLimit: number };
  }
}

interface BenchmarkResult {
  status: "passed" | "failed";
  generatedAtUtc: string;
  profile: {
    viewport: { width: number; height: number; devicePixelRatio: number };
    userAgent: string;
    hardwareConcurrency: number;
    network: "loopback-unthrottled";
  };
  corpus: string[];
  cold: { samples: QueryTiming[]; p95Ms: number };
  warm: { samples: QueryTiming[]; p95Ms: number };
  cancellation: {
    name: string;
    terminationMs: number;
    recoveryMs: number;
    recovered: boolean;
  }[];
  memory: {
    beforeJsHeapBytes: number | null;
    peakObservedJsHeapBytes: number | null;
    afterJsHeapBytes: number | null;
    failureCount: number;
    method: "performance.memory" | "unavailable";
  };
  errors: string[];
}

const DISTRICT = "12";
const QUERIES = [
  {
    name: "measure",
    sql: `select count(*) as statistical_records, count_if(pending_status) as pending_records,
      avg(duration_days) as mean_duration_days
      from governed_records where district_code = '${DISTRICT}'`,
  },
  {
    name: "grouped-chart",
    sql: `select nature_of_suit_family, count(*) as statistical_records,
      count_if(pending_status) as pending_records
      from governed_records where district_code = '${DISTRICT}'
      group by nature_of_suit_family order by statistical_records desc`,
  },
  {
    name: "row-page",
    sql: `select release_record_key, filed_month, pending_status, duration_days,
      nature_of_suit_family, identity_quality_status
      from governed_records where district_code = '${DISTRICT}'
      order by filed_month, release_record_key limit 100`,
  },
  {
    name: "bounded-sort",
    sql: `select release_record_key, duration_days, nature_of_suit_family, pending_status
      from governed_records where district_code = '${DISTRICT}'
      order by duration_days desc, release_record_key limit 200`,
  },
] as const;

const CANCELLATIONS = [
  {
    name: "scan",
    sql: `select sum(duration_days * i) from governed_records, range(100000) r(i)`,
  },
  {
    name: "group",
    sql: `select district_code, i % 100 as bucket, avg(duration_days)
      from governed_records, range(10000) r(i)
      group by district_code, bucket`,
  },
  {
    name: "sort",
    sql: `select release_record_key, duration_days, i
      from governed_records, range(10000) r(i)
      order by duration_days desc, i desc limit 100`,
  },
  {
    name: "export",
    sql: `copy (select * from governed_records, range(1000) r(i))
      to 'cancelled.csv' (format csv)`,
  },
] as const;

const errors: string[] = [];
window.__consoleErrors = errors;
window.addEventListener("error", (event) => errors.push(event.message));
window.addEventListener("unhandledrejection", (event) => errors.push(String(event.reason)));

function p95(values: number[]): number {
  const ordered = [...values].sort((left, right) => left - right);
  return ordered[Math.max(0, Math.ceil(ordered.length * 0.95) - 1)] ?? Number.NaN;
}

function heapBytes(): number | null {
  return performance.memory?.usedJSHeapSize ?? null;
}

function updateStatus(message: string, detail: string): void {
  const status = document.querySelector<HTMLElement>("#benchmark-status");
  const progress = document.querySelector<HTMLElement>("#benchmark-progress");
  const card = document.querySelector<HTMLElement>(".status-card");
  if (status) status.textContent = message;
  if (progress) progress.textContent = detail;
  if (card && /complete|failed/i.test(message)) card.setAttribute("aria-busy", "false");
}

async function runCorpus(engine: RowQueryEngine): Promise<QueryTiming[]> {
  const samples: QueryTiming[] = [];
  for (const query of QUERIES) {
    const timing = await engine.query(query.name, query.sql);
    if (timing.rows < 1) throw new Error(`${query.name} returned no rows`);
    samples.push(timing);
  }
  return samples;
}

async function runBenchmark(): Promise<BenchmarkResult> {
  const parameters = new URLSearchParams(window.location.search);
  const dataUrl = parameters.get("data");
  if (!dataUrl) throw new Error("Missing required data URL");
  const coldRuns = Math.min(Math.max(Number(parameters.get("coldRuns") ?? 3), 1), 5);
  const warmRuns = Math.min(Math.max(Number(parameters.get("warmRuns") ?? 5), 1), 10);
  const before = heapBytes();
  let peak = before;
  const observeHeap = () => {
    const observed = heapBytes();
    if (observed !== null) peak = Math.max(peak ?? 0, observed);
  };

  const cold: QueryTiming[] = [];
  for (let run = 0; run < coldRuns; run += 1) {
    updateStatus("Running uncached corpus", `Cold pass ${run + 1} of ${coldRuns}`);
    const engine = await RowQueryEngine.create(dataUrl);
    cold.push(...(await runCorpus(engine)));
    observeHeap();
    await engine.close();
  }

  updateStatus("Running cached corpus", `${warmRuns} bounded passes`);
  const warmEngine = await RowQueryEngine.create(dataUrl);
  const warm: QueryTiming[] = [];
  await runCorpus(warmEngine);
  for (let run = 0; run < warmRuns; run += 1) {
    warm.push(...(await runCorpus(warmEngine)));
    observeHeap();
  }
  await warmEngine.close();

  const cancellation: BenchmarkResult["cancellation"] = [];
  for (const probe of CANCELLATIONS) {
    updateStatus("Verifying cancellation", probe.name);
    const engine = await RowQueryEngine.create(dataUrl);
    const terminationMs = await engine.cancelByTerminatingWorker(probe.sql);
    const recovery = await RowQueryEngine.create(dataUrl);
    const recoveryTiming = await recovery.query(
      "recovery",
      "select count(*) as records from governed_records where district_code = '12'",
    );
    await recovery.close();
    cancellation.push({
      name: probe.name,
      terminationMs,
      recoveryMs: recoveryTiming.durationMs,
      recovered: recoveryTiming.rows === 1,
    });
    observeHeap();
  }

  return {
    status:
      errors.length === 0 && cancellation.every((probe) => probe.recovered)
        ? "passed"
        : "failed",
    generatedAtUtc: new Date().toISOString(),
    profile: {
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio,
      },
      userAgent: navigator.userAgent,
      hardwareConcurrency: navigator.hardwareConcurrency,
      network: "loopback-unthrottled",
    },
    corpus: QUERIES.map((query) => query.name),
    cold: { samples: cold, p95Ms: p95(cold.map((sample) => sample.durationMs)) },
    warm: { samples: warm, p95Ms: p95(warm.map((sample) => sample.durationMs)) },
    cancellation,
    memory: {
      beforeJsHeapBytes: before,
      peakObservedJsHeapBytes: peak,
      afterJsHeapBytes: heapBytes(),
      failureCount: errors.some((error) => /memory|allocation|out of bounds/i.test(error)) ? 1 : 0,
      method: performance.memory ? "performance.memory" : "unavailable",
    },
    errors: [...errors],
  };
}

async function main(): Promise<void> {
  try {
    const result = await runBenchmark();
    window.__m17Result = result;
    document.body.dataset.benchmarkStatus = result.status;
    updateStatus(result.status === "passed" ? "Benchmark complete" : "Benchmark failed", "Results ready");
    const output = document.querySelector<HTMLElement>("#benchmark-result");
    if (output) output.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errors.push(message);
    document.body.dataset.benchmarkStatus = "failed";
    updateStatus("Benchmark failed", message);
    const output = document.querySelector<HTMLElement>("#benchmark-result");
    if (output) output.textContent = JSON.stringify({ status: "failed", errors }, null, 2);
  }
}

void main();
