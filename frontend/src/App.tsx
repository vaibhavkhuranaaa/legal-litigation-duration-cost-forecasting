import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  api,
  type Benchmark,
  type Milestones,
  type Portfolio,
  type Provenance,
  type Readiness,
  type Scenario,
} from "./api";

echarts.use([BarChart, GridComponent, TooltipComponent, SVGRenderer]);

const cohorts = [
  ["ordinary_original", "Ordinary original"],
  ["multidistrict_litigation", "Multidistrict litigation"],
  ["other_procedural_origin", "Other procedural origin"],
  ["social_security_review", "Social Security review"],
] as const;

type Workspace = "portfolio" | "planner";

function percent(value: number, digits = 1) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: digits,
  }).format(value);
}

function number(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function currency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function BenchmarkChart({ benchmark }: { benchmark: Benchmark }) {
  const target = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!target.current) return;
    const chart = echarts.init(target.current, undefined, { renderer: "svg" });
    chart.setOption({
      animationDuration: 500,
      animationEasing: "cubicOut",
      grid: { left: 8, right: 24, top: 20, bottom: 8, containLabel: true },
      xAxis: {
        type: "value",
        min: 0,
        max: 1,
        axisLabel: { formatter: (value: number) => `${Math.round(value * 100)}%`, color: "#475569" },
        splitLine: { lineStyle: { color: "#dfe5e8" } },
      },
      yAxis: {
        type: "category",
        data: ["365 days", "730 days"],
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#17202a", fontWeight: 600 },
      },
      tooltip: { trigger: "axis", valueFormatter: (value: number) => percent(value) },
      series: [
        {
          type: "bar",
          data: [benchmark.termination_365_day_share, benchmark.termination_730_day_share],
          barWidth: 24,
          itemStyle: { color: "#087e8b", borderRadius: [0, 4, 4, 0] },
          label: { show: true, position: "right", formatter: ({ value }: { value: number }) => percent(value) },
        },
      ],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(target.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [benchmark]);

  return (
    <div
      ref={target}
      className="benchmark-chart"
      role="img"
      aria-label={`${percent(benchmark.termination_365_day_share)} terminated within 365 days and ${percent(benchmark.termination_730_day_share)} within 730 days among ${number(benchmark.cases)} observed ${benchmark.cohort.replaceAll("_", " ")} cases.`}
    />
  );
}

function CapabilityRibbon({ readiness }: { readiness: Readiness }) {
  const capabilities = [
    ["Observed portfolio", readiness.operations_analytics, "ready"],
    ["Duration forecast", readiness.duration_forecast, "blocked"],
    ["Docket events", readiness.milestone_events, "blocked"],
    ["Synthetic scenarios", readiness.scenario_engine, "ready"],
  ];
  return (
    <section className="capability-ribbon" aria-label="Capability readiness">
      {capabilities.map(([label, value, tone]) => (
        <div className="capability" key={label}>
          <span className={`status-mark ${tone}`} aria-hidden="true" />
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}

function ScenarioWorkbench() {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      setScenario(
        await api.scenario(Object.fromEntries(Object.entries(values).map(([key, value]) => [key, Number(value)]))),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scenario request failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="scenario-workbench" aria-labelledby="scenario-title">
      <div className="section-heading">
        <div>
          <p className="kicker synthetic">Synthetic planning</p>
          <h2 id="scenario-title">Test resource assumptions</h2>
        </div>
        <span className="evidence-tag synthetic">No observed cost data</span>
      </div>
      <form onSubmit={submit}>
        <label>Matters<input name="matters" type="number" min="1" max="10000" defaultValue="25" required /></label>
        <label>Months<input name="horizon_months" type="number" min="1" max="60" defaultValue="12" required /></label>
        <label>Attorney hours / matter / month<input name="attorney_hours_per_matter_month" type="number" min="0" max="500" step="0.5" defaultValue="4" required /></label>
        <label>Paralegal hours / matter / month<input name="paralegal_hours_per_matter_month" type="number" min="0" max="500" step="0.5" defaultValue="6" required /></label>
        <label>Attorney rate, synthetic USD<input name="attorney_rate_usd" type="number" min="0" max="5000" defaultValue="350" required /></label>
        <label>Paralegal rate, synthetic USD<input name="paralegal_rate_usd" type="number" min="0" max="5000" defaultValue="150" required /></label>
        <button className="primary-action" type="submit" disabled={pending}>
          {pending ? "Calculating..." : "Calculate scenario"}
        </button>
      </form>
      {error && <p className="inline-error" role="alert">{error}. Check API and retry.</p>}
      {!scenario && !error && <p className="empty-state">Enter assumptions to compare low, base, and high sensitivity cases.</p>}
      {scenario && (
        <div className="scenario-result" aria-live="polite">
          <div className="scenario-cases">
            {scenario.cases.map((item) => (
              <article key={item.name}>
                <span>{item.name}</span>
                <strong>{currency(item.budget_usd)}</strong>
                <p>{item.attorney_fte} attorney FTE · {item.paralegal_fte} paralegal FTE</p>
              </article>
            ))}
          </div>
          <p className="limitation">{scenario.limitation}</p>
        </div>
      )}
    </section>
  );
}

function App() {
  const [workspace, setWorkspace] = useState<Workspace>("portfolio");
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [milestones, setMilestones] = useState<Milestones | null>(null);
  const [provenance, setProvenance] = useState<Provenance | null>(null);
  const [cohort, setCohort] = useState("ordinary_original");
  const [error, setError] = useState("");
  const [requestKey, setRequestKey] = useState(0);

  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([api.readiness(), api.portfolio(), api.benchmark(cohort), api.milestones(), api.provenance()])
      .then(([nextReadiness, nextPortfolio, nextBenchmark, nextMilestones, nextProvenance]) => {
        if (!active) return;
        setReadiness(nextReadiness);
        setPortfolio(nextPortfolio);
        setBenchmark(nextBenchmark);
        setMilestones(nextMilestones);
        setProvenance(nextProvenance);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Data request failed");
      });
    return () => {
      active = false;
    };
  }, [cohort, requestKey]);

  function exportView() {
    const blob = new Blob([JSON.stringify({ portfolio, benchmark, milestones, provenance }, null, 2)], {
      type: "application/json",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "federal-civil-operations-view.json";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  if (error) {
    return (
      <main className="fatal-state">
        <p className="kicker refusal">Connection error</p>
        <h1>Operations data did not load</h1>
        <p>{error}. Start the local API, then retry.</p>
        <button className="primary-action" onClick={() => setRequestKey((value) => value + 1)}>Retry</button>
      </main>
    );
  }

  if (!readiness || !portfolio || !benchmark || !milestones || !provenance) {
    return (
      <main className="loading-state" aria-busy="true">
        <span className="loading-line" />
        <span className="loading-line wide" />
        <span className="loading-block" />
        <p>Loading governed operations evidence...</p>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="product-header">
        <div className="product-name">
          <span className="product-symbol" aria-hidden="true">FC</span>
          <div><strong>Federal Civil Operations</strong><span>Public metadata planning instrument</span></div>
        </div>
        <nav aria-label="Workspace">
          <button className={workspace === "portfolio" ? "active" : ""} onClick={() => setWorkspace("portfolio")}>Portfolio</button>
          <button className={workspace === "planner" ? "active" : ""} onClick={() => setWorkspace("planner")}>Matter planner</button>
        </nav>
        <button className="export-action" onClick={exportView}>Export evidence</button>
      </header>

      <CapabilityRibbon readiness={readiness} />

      <main>
        {workspace === "portfolio" ? (
          <div className="workspace-grid">
            <section className="evidence-field" aria-labelledby="portfolio-title">
              <div className="opening-statement">
                <div>
                  <p className="kicker observed">Observed portfolio</p>
                  <h1 id="portfolio-title">Nationwide workload, with failed capabilities left visible.</h1>
                  <p>{portfolio.interpretation}</p>
                </div>
                <div className="snapshot-stamp"><span>FJC snapshot</span><strong>{portfolio.source_snapshot}</strong><small>Nationwide civil records from 2010</small></div>
              </div>

              <div className="metric-band">
                <Metric label="Statistical records" value={number(portfolio.statistical_records)} note="Complete governed population" />
                <Metric label="Pending inventory" value={number(portfolio.pending_records)} note={`${percent(portfolio.pending_share)} of records`} />
                <Metric label="Collision-free cases" value={number(portfolio.collision_free_cases)} note="Case-level analytics boundary" />
                <Metric label="Reviewed RECAP matches" value={number(portfolio.promoted_recap_matches)} note={`${percent(portfolio.recap_match_coverage)} collision-free coverage`} />
              </div>

              <section className="benchmark-section" aria-labelledby="benchmark-title">
                <div className="section-heading">
                  <div><p className="kicker observed">Observed benchmark</p><h2 id="benchmark-title">Administrative termination varies by procedural cohort</h2></div>
                  <label className="cohort-control">Cohort<select value={cohort} onChange={(event) => setCohort(event.target.value)}>{cohorts.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
                </div>
                <div className="benchmark-layout">
                  <BenchmarkChart benchmark={benchmark} />
                  <div className="benchmark-notes">
                    <span className="evidence-tag observed">{number(benchmark.cases)} cases</span>
                    <dl><div><dt>Outcomes through</dt><dd>{benchmark.outcomes_through}</dd></div><div><dt>Snapshot censored</dt><dd>{percent(benchmark.snapshot_censored_share)}</dd></div></dl>
                    <p>{benchmark.limitation}</p>
                  </div>
                </div>
              </section>
            </section>

            <aside className="audit-rail" aria-labelledby="audit-title">
              <p className="kicker">Audit rail</p><h2 id="audit-title">What this release knows</h2>
              <dl>
                <div><dt>FJC source</dt><dd>{provenance.fjc_snapshot}</dd></div>
                <div><dt>RECAP source</dt><dd>{provenance.recap_snapshot}</dd></div>
                <div><dt>Model</dt><dd>Failed, not promoted</dd></div>
                <div><dt>Legal advice</dt><dd>No</dd></div>
                <div><dt>Real cost forecast</dt><dd>No</dd></div>
              </dl>
              <div className="refusal-note"><strong>Duration forecast unavailable</strong><p>{readiness.reason}</p></div>
              <div className="event-note"><strong>Docket events unavailable</strong><p>Missing {milestones.missing_event_fields.join(" and ")}. No event inferred.</p></div>
            </aside>
          </div>
        ) : (
          <div className="planner-grid">
            <section className="planner-boundary">
              <p className="kicker refusal">Forecast boundary</p>
              <h1>Matter duration cannot be estimated at required reliability.</h1>
              <p>No estimator passed every calibration and supported-slice gate. Use observed cohort benchmarks for context, then test your own resource assumptions.</p>
              <div className="boundary-actions"><button onClick={() => setWorkspace("portfolio")}>View observed cohorts</button><a href="#scenario-title">Plan synthetic resources</a></div>
              <small>Not legal advice. No predicted completion date is produced.</small>
            </section>
            <ScenarioWorkbench />
          </div>
        )}
      </main>

      <footer><span>Release contract v{provenance.release_version}</span><span>Observed metadata · explicit refusal · synthetic scenarios</span></footer>
    </div>
  );
}

export default App;
