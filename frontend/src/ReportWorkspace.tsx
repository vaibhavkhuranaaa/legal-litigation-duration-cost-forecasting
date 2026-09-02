import { type FormEvent, useMemo, useState } from "react";

import { CohortBenchmark, FilingTrend, PendingAge } from "./AnalyticsDashboard";
import { RecordExplorer } from "./RecordExplorer";
import {
  api,
  type Benchmark,
  type PopulationExplorer,
  type Portfolio,
  type Provenance,
  type Scenario,
} from "./api";
import {
  selectDistrictRanking,
  selectFilingSeries,
  selectLatestCompleteFilingChange,
  selectNatureRanking,
  selectPendingAgeSeries,
  selectPortfolioSlice,
  titleCase,
} from "./population";
import {
  parseReportState,
  reportLabel,
  reportPages,
  reportUrl,
  serializeReportState,
  type ReportId,
  type ReportState,
} from "./report-state";
import semanticRegistry from "./semantic-metrics.v1.json";

const integer = new Intl.NumberFormat("en-US");
const percent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });
const signedPercent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1, signDisplay: "always" });
const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const cohortOptions = [
  ["ordinary_original", "Ordinary original"],
  ["multidistrict_litigation", "Multidistrict litigation"],
  ["other_procedural_origin", "Other procedural origin"],
  ["social_security_review", "Social Security review"],
] as const;

const pageCopy: Record<ReportId, { title: string; description: string }> = {
  executive: {
    title: "Executive overview",
    description: "A governed 30-second read of workload, inventory pressure, observed duration, and evidence coverage.",
  },
  "filing-trends": {
    title: "Filing trends",
    description: "Annual filing cohorts, completed-year change, and observed status composition for the shared scope.",
  },
  "pending-aging": {
    title: "Pending inventory and aging",
    description: "Right-censored open-record volume by age band, with district concentration and explicit support.",
  },
  "case-mix": {
    title: "Case mix",
    description: "Nature-family composition and coverage under the active district scope.",
  },
  "district-comparison": {
    title: "District comparison",
    description: "Comparable published workload measures across districts, with drill-through into one district scope.",
  },
  "record-explorer": {
    title: "Record explorer",
    description: "Projected statistical records, deterministic sorting, bounded detail, and governed downloads for one annual partition.",
  },
  "data-quality": {
    title: "Data quality and coverage",
    description: "Identity collisions, mapping support, reviewed match availability, suppression, and reconciliation evidence.",
  },
  "scenario-methods": {
    title: "Scenario lab and methods",
    description: "Synthetic resource sensitivity, registered measures, provenance, and capability refusals in one methods workspace.",
  },
};

type NavigationMode = "push" | "replace";

type ReportWorkspaceProps = {
  portfolio: Portfolio;
  explorer: PopulationExplorer;
  benchmark: Benchmark;
  provenance: Provenance;
  state: ReportState;
  onStateChange: (state: ReportState, mode: NavigationMode) => void;
};

type Bookmark = {
  id: string;
  name: string;
  url: string;
};

const bookmarkStorageKey = "federal-civil-report-bookmarks.v1";

function readBookmarks(): Bookmark[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(bookmarkStorageKey) ?? "[]") as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is Bookmark => {
      if (!item || typeof item !== "object") return false;
      const value = item as Record<string, unknown>;
      return typeof value.id === "string" && typeof value.name === "string" && typeof value.url === "string";
    }).slice(0, 12);
  } catch {
    return [];
  }
}

function ScopeHeading({ explorer, state }: { explorer: PopulationExplorer; state: ReportState }) {
  const district = explorer.dimensions.districts.find((item) => item.district_code === state.districtCode);
  return (
    <>
      {district ? `${district.ao_label} / ${district.court_id.toUpperCase()}` : "All 94 districts"}
      {" / "}
      {state.natureFamily === "all" ? "All case families" : titleCase(state.natureFamily)}
    </>
  );
}

function PageHeading({ explorer, state }: { explorer: PopulationExplorer; state: ReportState }) {
  const copy = pageCopy[state.report];
  return (
    <section className="report-heading" aria-labelledby="report-title">
      <div>
        <h1 id="report-title">{copy.title}</h1>
        <p>{copy.description}</p>
      </div>
      <div className="snapshot-block">
        <span>Aggregate fast path</span>
        <strong>{explorer.source_snapshot}</strong>
        <small>Registered metrics / publication threshold {integer.format(explorer.publication_policy.minimum_support)}</small>
      </div>
    </section>
  );
}

function EmptyState({ onClear }: { onClear: () => void }) {
  return (
    <section className="bounded-state empty-state" role="status">
      <h2>No published aggregate cells for the active scope</h2>
      <p>Broaden the district or case-family filter. Empty and support-withheld results never become zero.</p>
      <button className="button-secondary" type="button" onClick={onClear}>Clear analytical scope</button>
    </section>
  );
}

function MetricStrip({ children, label }: { children: React.ReactNode; label: string }) {
  return <section className="metric-strip" aria-label={label}>{children}</section>;
}

type ScopePageProps = {
  portfolio: Portfolio;
  explorer: PopulationExplorer;
  benchmark: Benchmark;
  provenance: Provenance;
  state: ReportState;
  update: (patch: Partial<ReportState>, mode?: NavigationMode) => void;
  clearScope: () => void;
};

function ExecutivePage({ portfolio, explorer, benchmark, state, update, clearScope }: ScopePageProps) {
  const filters = { districtCode: state.districtCode, natureFamily: state.natureFamily };
  const slice = selectPortfolioSlice(explorer, filters);
  const filingChange = selectLatestCompleteFilingChange(explorer, filters);
  const pendingAge = selectPendingAgeSeries(explorer, filters);
  const oldestPending = pendingAge.find((row) => row.age_band === "5_years_or_more");
  const oldestShare = slice && oldestPending && slice.pending_records > 0 ? oldestPending.pending_records / slice.pending_records : null;
  const districtRanking = selectDistrictRanking(explorer, state.natureFamily);
  const natureRanking = selectNatureRanking(explorer, state.districtCode);
  const ranking = state.rankingMode === "district" ? districtRanking : natureRanking;

  if (!slice) return <EmptyState onClear={clearScope} />;
  return (
    <>
      <MetricStrip label="Executive summary measures">
        <article><span>Statistical records</span><strong>{integer.format(slice.total_records)}</strong><small>{percent.format(slice.total_records / portfolio.statistical_records)} of nationwide records</small></article>
        <article><span>Pending inventory</span><strong>{integer.format(slice.pending_records)}</strong><small>{percent.format(slice.pending_share)} of selected records</small></article>
        <article><span>Observed mean duration</span><strong>{slice.average_observed_duration_days === null ? "Withheld" : `${Math.round(slice.average_observed_duration_days)} days`}</strong><small>Terminated records only / not a forecast</small></article>
        <article><span>Latest complete year</span><strong>{filingChange ? signedPercent.format(filingChange.change) : "Insufficient history"}</strong><small>{filingChange ? `${filingChange.currentYear} versus ${filingChange.previousYear}` : "Two supported years required"}</small></article>
      </MetricStrip>

      <section className="scope-brief" aria-label="Executive interpretation">
        <div><span>Portfolio signal</span><strong>{percent.format(slice.pending_share)} pending; {oldestShare === null ? "oldest band withheld" : `${percent.format(oldestShare)} of pending records are at least five years old`}.</strong></div>
        <dl>
          <div><dt>Observed terminations</dt><dd>{slice.observed_terminations === null ? "Withheld" : integer.format(slice.observed_terminations)}</dd></div>
          <div><dt>RECAP match coverage</dt><dd>{percent.format(slice.match_coverage)}</dd></div>
          <div><dt>Mapped nature records</dt><dd>{percent.format(slice.supported_nature_records / slice.total_records)}</dd></div>
        </dl>
      </section>

      <div className="analytics-grid">
        <section className="analysis-panel trend-panel" aria-labelledby="executive-filings-title">
          <div className="panel-heading"><div><h2 id="executive-filings-title">Filing volume</h2><p>Annual aggregate cohorts. The final year is partial through the snapshot date.</p></div><button className="text-action" type="button" onClick={() => update({ report: "filing-trends", drillFrom: "executive" }, "push")}>Open filing detail</button></div>
          <FilingTrend explorer={explorer} filters={filters} />
        </section>
        <section className="analysis-panel ranking-panel" aria-labelledby="executive-ranking-title">
          <div className="panel-heading ranking-heading">
            <div><h2 id="executive-ranking-title">Workload concentration</h2><p>Select a published row to cross-filter and drill into its report.</p></div>
            <div className="segmented-control" role="group" aria-label="Ranking dimension">
              <button type="button" aria-pressed={state.rankingMode === "district"} onClick={() => update({ rankingMode: "district" })}>Districts</button>
              <button type="button" aria-pressed={state.rankingMode === "nature"} onClick={() => update({ rankingMode: "nature" })}>Case families</button>
            </div>
          </div>
          <div className="table-wrap"><table>
            <thead><tr><th scope="col">Rank</th><th scope="col">{state.rankingMode === "district" ? "District" : "Case family"}</th><th scope="col">Records</th><th scope="col">Pending</th><th scope="col">Pending share</th></tr></thead>
            <tbody>{ranking.slice(0, 8).map((row, index) => <tr key={row.key}>
              <td>{index + 1}</td><th scope="row"><button className="rank-link" type="button" onClick={() => update(state.rankingMode === "district" ? { districtCode: row.key, report: "district-comparison", drillFrom: "executive" } : { natureFamily: row.key, report: "case-mix", drillFrom: "executive" }, "push")}>{row.label}</button></th><td>{integer.format(row.total_records)}</td><td>{integer.format(row.pending_records)}</td><td>{percent.format(row.pending_share)}</td>
            </tr>)}</tbody>
          </table></div>
          <p className="panel-footnote">Row selection updates the shared scope, URL, chips, and every compatible report.</p>
        </section>
        <section className="analysis-panel" aria-labelledby="executive-aging-title">
          <div className="panel-heading"><div><h2 id="executive-aging-title">Pending inventory age</h2><p>Right-censored age at the data cutoff.</p></div><button className="text-action" type="button" onClick={() => update({ report: "pending-aging", drillFrom: "executive" }, "push")}>Open aging detail</button></div>
          <PendingAge explorer={explorer} filters={filters} />
        </section>
        <section className="analysis-panel" aria-labelledby="executive-cohort-title">
          <div className="panel-heading"><div><h2 id="executive-cohort-title">Historical cohort context</h2><p>{titleCase(benchmark.cohort)} / descriptive observed outcomes.</p></div><span>{integer.format(benchmark.cases)} cases</span></div>
          <CohortBenchmark benchmark={benchmark} />
          <p className="panel-footnote">{benchmark.limitation}</p>
        </section>
      </div>
    </>
  );
}

function FilingTrendsPage({ explorer, state, clearScope }: ScopePageProps) {
  const filters = { districtCode: state.districtCode, natureFamily: state.natureFamily };
  const series = selectFilingSeries(explorer, filters).sort((left, right) => left.filing_year - right.filing_year);
  const slice = selectPortfolioSlice(explorer, filters);
  const change = selectLatestCompleteFilingChange(explorer, filters);
  if (!slice || series.length === 0) return <EmptyState onClear={clearScope} />;
  const latestComplete = series.filter((row) => row.filing_year < Number(explorer.source_snapshot.slice(0, 4))).at(-1);
  return <>
    <MetricStrip label="Filing trend measures">
      <article><span>Published years</span><strong>{series.length}</strong><small>{series[0]?.filing_year} through {series.at(-1)?.filing_year}</small></article>
      <article><span>Latest complete-year filings</span><strong>{latestComplete ? integer.format(latestComplete.cohort_records) : "Unavailable"}</strong><small>{latestComplete?.filing_year ?? "No supported year"}</small></article>
      <article><span>Year-over-year change</span><strong>{change ? signedPercent.format(change.change) : "Unavailable"}</strong><small>Completed years only</small></article>
      <article><span>Selected total records</span><strong>{integer.format(slice.total_records)}</strong><small>All filing cohorts in scope</small></article>
    </MetricStrip>
    <div className="report-grid report-grid-wide">
      <section className="analysis-panel" aria-labelledby="filing-chart-title"><div className="panel-heading"><div><h2 id="filing-chart-title">Annual filing cohorts</h2><p>Observed record counts; {explorer.source_snapshot.slice(0, 4)} is partial.</p></div><span>{series.length} published points</span></div><FilingTrend explorer={explorer} filters={filters} /></section>
      <section className="analysis-panel" aria-labelledby="filing-table-title"><div className="panel-heading"><div><h2 id="filing-table-title">Annual evidence table</h2><p>Terminations and pending status are observed through the snapshot cutoff.</p></div></div><div className="table-wrap"><table><thead><tr><th scope="col">Year</th><th scope="col">Filed</th><th scope="col">Terminated</th><th scope="col">Pending</th><th scope="col">Matched</th></tr></thead><tbody>{[...series].reverse().map((row) => <tr key={row.filing_year}><th scope="row">{row.filing_year}{row.filing_year === Number(explorer.source_snapshot.slice(0, 4)) ? " · partial" : ""}</th><td>{integer.format(row.cohort_records)}</td><td>{integer.format(row.observed_terminations)}</td><td>{integer.format(row.pending_records)}</td><td>{integer.format(row.matched_records)}</td></tr>)}</tbody></table></div></section>
    </div>
  </>;
}

function PendingAgingPage({ explorer, state, update, clearScope }: ScopePageProps) {
  const filters = { districtCode: state.districtCode, natureFamily: state.natureFamily };
  const slice = selectPortfolioSlice(explorer, filters);
  const ages = selectPendingAgeSeries(explorer, filters);
  if (!slice || ages.length === 0) return <EmptyState onClear={clearScope} />;
  const oldest = ages.find((row) => row.age_band === "5_years_or_more");
  const districts = selectDistrictRanking(explorer, state.natureFamily).filter((row) => row.pending_records > 0);
  const weightedAge = ages.reduce((sum, row) => sum + row.average_age_days * row.pending_records, 0) / Math.max(1, ages.reduce((sum, row) => sum + row.pending_records, 0));
  return <>
    <MetricStrip label="Pending inventory measures">
      <article><span>Pending records</span><strong>{integer.format(slice.pending_records)}</strong><small>{percent.format(slice.pending_share)} of the selected portfolio</small></article>
      <article><span>Average pending age</span><strong>{Math.round(weightedAge)} days</strong><small>Right-censored age / not time remaining</small></article>
      <article><span>Five years or older</span><strong>{oldest ? integer.format(oldest.pending_records) : "Withheld"}</strong><small>{oldest ? percent.format(oldest.pending_records / slice.pending_records) : "Below support"}</small></article>
      <article><span>Matched pending</span><strong>{integer.format(ages.reduce((sum, row) => sum + row.matched_pending_records, 0))}</strong><small>Reviewed identity-match availability</small></article>
    </MetricStrip>
    <div className="report-grid">
      <section className="analysis-panel" aria-labelledby="pending-chart-title"><div className="panel-heading"><div><h2 id="pending-chart-title">Age-band distribution</h2><p>Amber marks the oldest published right-censored band.</p></div><span>{ages.length}/{explorer.dimensions.age_bands.length} bands</span></div><PendingAge explorer={explorer} filters={filters} /></section>
      <section className="analysis-panel" aria-labelledby="pending-district-title"><div className="panel-heading"><div><h2 id="pending-district-title">District concentration</h2><p>Select a district to cross-filter and drill through.</p></div></div><div className="table-wrap"><table><thead><tr><th scope="col">District</th><th scope="col">Pending</th><th scope="col">Share</th></tr></thead><tbody>{districts.slice(0, 10).map((row) => <tr key={row.key}><th scope="row"><button className="rank-link" type="button" onClick={() => update({ districtCode: row.key, report: "district-comparison", drillFrom: "pending-aging" }, "push")}>{row.label}</button></th><td>{integer.format(row.pending_records)}</td><td>{percent.format(row.pending_share)}</td></tr>)}</tbody></table></div></section>
    </div>
  </>;
}

function CaseMixPage({ explorer, state, update, clearScope }: ScopePageProps) {
  const rows = selectNatureRanking(explorer, state.districtCode);
  if (rows.length === 0) return <EmptyState onClear={clearScope} />;
  const total = rows.reduce((sum, row) => sum + row.total_records, 0);
  return <div className="report-grid report-grid-wide">
    <section className="analysis-panel mix-ledger" aria-labelledby="case-mix-title"><div className="panel-heading"><div><h2 id="case-mix-title">Nature-family composition</h2><p>Choose a family to update the shared scope, chips, URL, and dependent pages.</p></div><span>{rows.length} published families</span></div><div className="composition-list">{rows.map((row) => <button type="button" key={row.key} className={state.natureFamily === row.key ? "composition-row selected" : "composition-row"} onClick={() => update({ natureFamily: row.key })}><span><strong>{row.label}</strong><small>{integer.format(row.total_records)} records</small></span><span className="composition-bar" aria-hidden="true"><i style={{ width: `${Math.max(1.5, row.total_records / total * 100)}%` }} /></span><b>{percent.format(row.total_records / total)}</b></button>)}</div></section>
    <section className="analysis-panel" aria-labelledby="case-mix-detail-title"><div className="panel-heading"><div><h2 id="case-mix-detail-title">Published comparison</h2><p>Administrative case-mix categories; not legal classifications or advice.</p></div></div><div className="table-wrap"><table><thead><tr><th scope="col">Case family</th><th scope="col">Records</th><th scope="col">Pending</th><th scope="col">Match coverage</th></tr></thead><tbody>{rows.map((row) => <tr key={row.key} className={state.natureFamily === row.key ? "selected-row" : ""}><th scope="row"><button className="rank-link" type="button" onClick={() => update({ natureFamily: row.key })}>{row.label}</button></th><td>{integer.format(row.total_records)}</td><td>{integer.format(row.pending_records)}</td><td>{percent.format(row.match_coverage)}</td></tr>)}</tbody></table></div></section>
  </div>;
}

function DistrictComparisonPage({ explorer, state, update, clearScope }: ScopePageProps) {
  const rows = selectDistrictRanking(explorer, state.natureFamily);
  if (rows.length === 0) return <EmptyState onClear={clearScope} />;
  const selected = rows.find((row) => row.key === state.districtCode);
  const national = selectPortfolioSlice(explorer, { districtCode: "all", natureFamily: state.natureFamily });
  return <>
    {selected && national && <section className="scope-brief" aria-label="Selected district comparison"><div><span>Selected district</span><strong>{selected.label} holds {percent.format(selected.total_records / national.total_records)} of the comparable published workload.</strong></div><dl><div><dt>Records</dt><dd>{integer.format(selected.total_records)}</dd></div><div><dt>Pending share</dt><dd>{percent.format(selected.pending_share)}</dd></div><div><dt>Match coverage</dt><dd>{percent.format(selected.match_coverage)}</dd></div></dl></section>}
    <section className="analysis-panel district-ledger" aria-labelledby="district-table-title"><div className="panel-heading"><div><h2 id="district-table-title">District workload comparison</h2><p>Sorted by pending inventory. Selecting a row cross-filters the complete workspace.</p></div><span>{rows.length} published districts</span></div><div className="table-wrap"><table><thead><tr><th scope="col">Rank</th><th scope="col">District</th><th scope="col">Records</th><th scope="col">Pending</th><th scope="col">Pending share</th><th scope="col">Observed mean duration</th><th scope="col">Match coverage</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.key} className={row.key === state.districtCode ? "selected-row" : ""}><td>{index + 1}</td><th scope="row"><button className="rank-link" type="button" onClick={() => update({ districtCode: row.key })}>{row.label}</button></th><td>{integer.format(row.total_records)}</td><td>{integer.format(row.pending_records)}</td><td>{percent.format(row.pending_share)}</td><td>{row.average_observed_duration_days === null ? "Withheld" : `${Math.round(row.average_observed_duration_days)} days`}</td><td>{percent.format(row.match_coverage)}</td></tr>)}</tbody></table></div></section>
  </>;
}

function RecordExplorerPage({ explorer, state, clearScope }: ScopePageProps) {
  const slice = selectPortfolioSlice(explorer, { districtCode: state.districtCode, natureFamily: state.natureFamily });
  if (!slice) return <EmptyState onClear={clearScope} />;
  return <RecordExplorer districtCode={state.districtCode} natureFamily={state.natureFamily} aggregateRecords={slice.total_records} onClearScope={clearScope} />;
}

function DataQualityPage({ portfolio, explorer, state, provenance, clearScope }: ScopePageProps) {
  const slice = selectPortfolioSlice(explorer, { districtCode: state.districtCode, natureFamily: state.natureFamily });
  if (!slice) return <EmptyState onClear={clearScope} />;
  const collisions = slice.total_records - slice.collision_free_records;
  return <>
    <MetricStrip label="Data quality measures">
      <article><span>Collision-free records</span><strong>{percent.format(slice.collision_free_records / slice.total_records)}</strong><small>{integer.format(collisions)} collision-labeled records retained</small></article>
      <article><span>Nature mapping support</span><strong>{percent.format(slice.supported_nature_records / slice.total_records)}</strong><small>Unsupported legacy values remain labeled</small></article>
      <article><span>RECAP match availability</span><strong>{percent.format(slice.match_coverage)}</strong><small>{integer.format(slice.matched_records)} reviewed matches</small></article>
      <article><span>Aggregate reconciliation</span><strong>Exact</strong><small>8,970 supported slices / zero exact error</small></article>
    </MetricStrip>
    <div className="quality-ledger">
      <section className="analysis-panel" aria-labelledby="quality-identity-title"><div className="panel-heading"><div><h2 id="quality-identity-title">Identity and coverage</h2><p>One statistical record is not guaranteed to represent one unique case.</p></div></div><dl><div><dt>Nationwide records</dt><dd>{integer.format(portfolio.statistical_records)}</dd></div><div><dt>Selected collision labels</dt><dd>{integer.format(collisions)}</dd></div><div><dt>Selected mapped records</dt><dd>{integer.format(slice.supported_nature_records)}</dd></div><div><dt>Selected reviewed matches</dt><dd>{integer.format(slice.matched_records)}</dd></div></dl></section>
      <section className="analysis-panel" aria-labelledby="quality-contract-title"><div className="panel-heading"><div><h2 id="quality-contract-title">Publication contract</h2><p>{explorer.publication_policy.limitation}</p></div></div><dl><div><dt>Minimum aggregate support</dt><dd>{integer.format(explorer.publication_policy.minimum_support)}</dd></div><div><dt>Matter-level rows in cube</dt><dd>{explorer.publication_policy.matter_level_rows}</dd></div><div><dt>FJC snapshot</dt><dd>{provenance.fjc_snapshot}</dd></div><div><dt>RECAP snapshot</dt><dd>{provenance.recap_snapshot}</dd></div></dl></section>
      <section className="analysis-panel" aria-labelledby="quality-reconciliation-title"><div className="panel-heading"><div><h2 id="quality-reconciliation-title">Release evidence</h2><p>The local serving mart and semantic registry reproduce the approved aggregate cube.</p></div></div><ul className="evidence-list"><li><strong>5,008,334</strong><span>statistical rows retained</span></li><li><strong>362,615</strong><span>collision labels retained</span></li><li><strong>55,158</strong><span>exact semantic comparisons</span></li><li><strong>0</strong><span>exact reconciliation error</span></li></ul></section>
    </div>
  </>;
}

function ScenarioMethodsPage({ explorer, provenance }: ScopePageProps) {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      setScenario(await api.scenario(Object.fromEntries(Object.entries(values).map(([key, value]) => [key, Number(value)]))));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scenario calculation failed");
    } finally {
      setPending(false);
    }
  }

  return <>
    <section className="scenario-band" aria-labelledby="scenario-title">
      <div className="scenario-inputs"><div className="panel-heading"><div><h2 id="scenario-title">Synthetic resource sensitivity</h2><p>Bounded user assumptions remain visually and analytically separate from observed evidence.</p></div><span>Synthetic / deterministic</span></div><form onSubmit={submit}><label>Matters<input name="matters" type="number" min="1" max="10000" defaultValue="25" required /></label><label>Horizon, months<input name="horizon_months" type="number" min="1" max="60" defaultValue="12" required /></label><label>Attorney hours / matter-month<input name="attorney_hours_per_matter_month" type="number" min="0" max="500" step="0.5" defaultValue="4" required /></label><label>Paralegal hours / matter-month<input name="paralegal_hours_per_matter_month" type="number" min="0" max="500" step="0.5" defaultValue="6" required /></label><label>Synthetic attorney rate<input name="attorney_rate_usd" type="number" min="0" max="5000" defaultValue="350" required /></label><label>Synthetic paralegal rate<input name="paralegal_rate_usd" type="number" min="0" max="5000" defaultValue="150" required /></label><button className="button-primary" type="submit" disabled={pending}>{pending ? "Calculating sensitivity" : "Calculate sensitivity"}</button></form>{error && <p className="inline-error" role="alert">{error}. Verify the runtime and try again.</p>}</div>
      <div className="scenario-output"><div className="panel-heading"><div><h2>Sensitivity cases</h2><p>Low, base, and high cases apply 0.80, 1.00, and 1.25 multipliers.</p></div></div>{!scenario && !error && <div className="scenario-empty"><strong>Ready for assumptions</strong><p>Calculate once to compare staffing capacity and synthetic budget exposure.</p></div>}{scenario && <div className="scenario-results" aria-live="polite"><div className="table-wrap"><table><thead><tr><th scope="col">Case</th><th scope="col">Attorney FTE</th><th scope="col">Paralegal FTE</th><th scope="col">Synthetic budget</th></tr></thead><tbody>{scenario.cases.map((item) => <tr key={item.name} className={item.name === "base" ? "selected-row" : ""}><th scope="row">{item.name}</th><td>{item.attorney_fte.toFixed(2)}</td><td>{item.paralegal_fte.toFixed(2)}</td><td>{currency.format(item.budget_usd)}</td></tr>)}</tbody></table></div><p className="panel-footnote">{scenario.limitation}</p></div>}</div>
    </section>
    <details className="methodology" open><summary><span>Registered metrics and capability boundaries</span><small>{semanticRegistry.registry_id} / contract v{provenance.release_version}</small></summary><div className="methods-layout"><section><h3>Semantic measures</h3><div className="metric-definitions">{semanticRegistry.measures.map((measure) => <details key={measure.id}><summary>{measure.label}<small>{measure.format}</small></summary><p>{measure.definition}</p><p><strong>Limitation:</strong> {measure.limitation}</p></details>)}</div></section><section><h3>Capability boundary</h3><dl><div><dt>Operations analytics</dt><dd>Available</dd></div><div><dt>Duration forecast</dt><dd>Refused</dd></div><div><dt>Docket-event enrichment</dt><dd>Refused</dd></div><div><dt>Scenario method</dt><dd>Synthetic</dd></div><div><dt>Legal advice</dt><dd>No</dd></div></dl><p>Historical aggregates describe observed administrative records. They do not predict a matter, classify a legal outcome, or provide legal advice.</p></section><section><h3>Source lineage</h3><dl><div><dt>Dataset</dt><dd>{semanticRegistry.dataset_version}</dd></div><div><dt>FJC snapshot</dt><dd>{provenance.fjc_snapshot}</dd></div><div><dt>RECAP snapshot</dt><dd>{provenance.recap_snapshot}</dd></div><div><dt>Minimum support</dt><dd>{integer.format(explorer.publication_policy.minimum_support)}</dd></div></dl></section></div></details>
  </>;
}

export function ReportWorkspace({ portfolio, explorer, benchmark, provenance, state, onStateChange }: ReportWorkspaceProps) {
  const [scopeExpanded, setScopeExpanded] = useState(false);
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>(readBookmarks);
  const district = explorer.dimensions.districts.find((item) => item.district_code === state.districtCode);
  const scopeLabel = `${district ? district.ao_label : "All 94 districts"} / ${state.natureFamily === "all" ? "All case families" : titleCase(state.natureFamily)}`;
  const activeFilters = [
    ...(district ? [{ key: "district", label: `District: ${district.ao_label}` }] : []),
    ...(state.natureFamily !== "all" ? [{ key: "nature", label: `Case family: ${titleCase(state.natureFamily)}` }] : []),
    ...(state.cohort !== "ordinary_original" ? [{ key: "cohort", label: `Cohort: ${titleCase(state.cohort)}` }] : []),
  ];

  function update(patch: Partial<ReportState>, mode: NavigationMode = "replace") {
    onStateChange({ ...state, ...patch }, mode);
  }

  function openReport(report: ReportId) {
    update({ report, drillFrom: undefined }, "push");
    setMobileMoreOpen(false);
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function clearScope() {
    update({ districtCode: "all", natureFamily: "all", drillFrom: undefined });
  }

  function saveBookmark() {
    const url = reportUrl(state, window.location.pathname);
    const name = `${reportLabel(state.report)} · ${scopeLabel}`;
    const existing = bookmarks.find((bookmark) => bookmark.url === url);
    const next = existing ? bookmarks.map((bookmark) => bookmark.id === existing.id ? { ...bookmark, name } : bookmark) : [{ id: crypto.randomUUID(), name, url }, ...bookmarks].slice(0, 12);
    setBookmarks(next);
    window.localStorage.setItem(bookmarkStorageKey, JSON.stringify(next));
  }

  function restoreBookmark(bookmark: Bookmark) {
    const url = new URL(bookmark.url, window.location.origin);
    onStateChange(parseReportState(url.search), "push");
  }

  function removeBookmark(id: string) {
    const next = bookmarks.filter((bookmark) => bookmark.id !== id);
    setBookmarks(next);
    window.localStorage.setItem(bookmarkStorageKey, JSON.stringify(next));
  }

  const pageProps = { portfolio, explorer, benchmark, provenance, state, update, clearScope };
  const page = useMemo(() => {
    switch (state.report) {
      case "filing-trends": return <FilingTrendsPage {...pageProps} />;
      case "pending-aging": return <PendingAgingPage {...pageProps} />;
      case "case-mix": return <CaseMixPage {...pageProps} />;
      case "district-comparison": return <DistrictComparisonPage {...pageProps} />;
      case "record-explorer": return <RecordExplorerPage {...pageProps} />;
      case "data-quality": return <DataQualityPage {...pageProps} />;
      case "scenario-methods": return <ScenarioMethodsPage {...pageProps} />;
      default: return <ExecutivePage {...pageProps} />;
    }
  }, [benchmark, explorer, portfolio, provenance, state]);

  return <div className="enterprise-shell">
    <aside className="side-navigation">
      <div className="brand-block"><span className="brand-mark" aria-hidden="true">FC</span><div><strong>Federal Civil</strong><span>Portfolio Intelligence</span></div></div>
      <nav aria-label="Report navigation">
        {reportPages.slice(0, 3).map((item) => <button type="button" key={item.id} className={state.report === item.id ? "active" : ""} aria-current={state.report === item.id ? "page" : undefined} onClick={() => openReport(item.id)}><span>{item.shortLabel}</span><small>{item.description}</small></button>)}
        <button className="mobile-more-trigger" type="button" aria-expanded={mobileMoreOpen} aria-controls="secondary-navigation" onClick={() => setMobileMoreOpen((value) => !value)}><span>More</span><small>Five reports</small></button>
        <div className={`nav-more${mobileMoreOpen ? " open" : ""}`} id="secondary-navigation">{reportPages.slice(3).map((item) => <button type="button" key={item.id} className={state.report === item.id ? "active" : ""} aria-current={state.report === item.id ? "page" : undefined} onClick={() => openReport(item.id)}><span>{item.shortLabel}</span><small>{item.description}</small></button>)}</div>
      </nav>
      <div className="side-status"><span>Eight-report workspace</span><small>Aggregate fast path / {explorer.source_snapshot}</small></div>
    </aside>

    <main className="product-workspace">
      <header className="workspace-bar">
        <div><strong>{reportLabel(state.report)}</strong><span>{integer.format(portfolio.statistical_records)} governed records / shared analytical context</span></div>
        <div className="workspace-actions"><span className="release-state">Contract v{provenance.release_version}</span><details className="bookmark-menu"><summary>Saved views ({bookmarks.length})</summary><div><button className="button-primary" type="button" onClick={saveBookmark}>Save current view</button>{bookmarks.length === 0 ? <p>No saved views on this browser.</p> : <ul>{bookmarks.map((bookmark) => <li key={bookmark.id}><button type="button" onClick={() => restoreBookmark(bookmark)}>{bookmark.name}</button><button type="button" aria-label={`Remove ${bookmark.name}`} onClick={() => removeBookmark(bookmark.id)}>Remove</button></li>)}</ul>}</div></details></div>
      </header>

      <section className={`query-bar report-query-bar${scopeExpanded ? " expanded" : ""}`} aria-label="Shared analytical scope">
        <div className="query-title"><span>Active analytical scope</span><strong>{scopeLabel}</strong></div>
        <button className="mobile-scope-toggle" type="button" aria-expanded={scopeExpanded} onClick={() => setScopeExpanded((value) => !value)}>{scopeExpanded ? "Close filters" : "Filters"}</button>
        <label>District<select data-testid="district-filter" value={state.districtCode} onChange={(event) => update({ districtCode: event.target.value, drillFrom: undefined })}><option value="all">All 94 districts</option>{explorer.dimensions.districts.map((item) => <option value={item.district_code} key={item.district_code}>{item.ao_label} / {item.court_id.toUpperCase()}</option>)}</select></label>
        <label>Case family<select data-testid="nature-filter" value={state.natureFamily} onChange={(event) => update({ natureFamily: event.target.value, drillFrom: undefined })}><option value="all">All {explorer.dimensions.nature_families.length} families</option>{explorer.dimensions.nature_families.map((item) => <option value={item} key={item}>{titleCase(item)}</option>)}</select></label>
        <div className="filing-contract"><span>Filing period</span><strong>2010 to 2026 snapshot</strong></div>
        <label>Cohort context<select data-testid="cohort-filter" value={state.cohort} onChange={(event) => update({ cohort: event.target.value })}>{cohortOptions.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
        <div className="query-actions"><button className="button-secondary" type="button" onClick={clearScope} disabled={activeFilters.length === 0}>Clear</button></div>
      </section>

      <div className="report-workspace">
        <div className="context-row">
          {state.drillFrom && <nav className="breadcrumbs" aria-label="Drill-through breadcrumb"><button type="button" onClick={() => update({ report: state.drillFrom, drillFrom: undefined }, "push")}>{reportLabel(state.drillFrom)}</button><span aria-hidden="true">/</span><span aria-current="page">{reportLabel(state.report)}</span></nav>}
          <div className="active-filter-chips" role="group" aria-label="Active filters">{activeFilters.length === 0 ? <span className="all-scope-chip">No optional filters</span> : activeFilters.map((filter) => <button type="button" key={filter.key} aria-label={`Remove ${filter.label}`} onClick={() => update(filter.key === "district" ? { districtCode: "all", drillFrom: undefined } : filter.key === "nature" ? { natureFamily: "all", drillFrom: undefined } : { cohort: "ordinary_original" })}>{filter.label}<span className="chip-remove-icon" aria-hidden="true" /></button>)}</div>
          <span className="url-state" title={serializeReportState(state)}>URL state synchronized</span>
        </div>
        <p className="visually-hidden" aria-live="polite"><ScopeHeading explorer={explorer} state={state} />. {activeFilters.length} optional filters active.</p>
        <PageHeading explorer={explorer} state={state} />
        {page}
      </div>
    </main>
  </div>;
}
