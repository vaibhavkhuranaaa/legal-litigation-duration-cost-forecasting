import type { EChartsCoreOption, EChartsType } from "echarts/core";
import { useEffect, useMemo, useRef, useState } from "react";

import type {
  Benchmark,
  Milestones,
  PopulationExplorer,
  Portfolio,
  Provenance,
  Readiness,
} from "./api";
import {
  type PopulationFilters,
  selectDistrictRanking,
  selectFilingSeries,
  selectLatestCompleteFilingChange,
  selectNatureRanking,
  selectPendingAgeSeries,
  selectPortfolioSlice,
  titleCase,
} from "./population";

const chartAnimationDuration = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 360;
const loadChartEngine = () => import("./chart-engine").then(({ echarts }) => echarts);

function mountChart(target: HTMLDivElement, option: EChartsCoreOption) {
  let cancelled = false;
  let chart: EChartsType | null = null;
  let observer: ResizeObserver | null = null;
  target.dataset.chartStatus = "loading";
  void loadChartEngine()
    .then((echarts) => {
      if (cancelled) return;
      chart = echarts.init(target, undefined, { renderer: "svg" });
      chart.setOption(option);
      observer = new ResizeObserver(() => chart?.resize());
      observer.observe(target);
      target.dataset.chartStatus = "ready";
    })
    .catch(() => {
      if (!cancelled) target.dataset.chartStatus = "unavailable";
    });
  return () => {
    cancelled = true;
    observer?.disconnect();
    chart?.dispose();
  };
}

const cohorts = [
  ["ordinary_original", "Ordinary original"],
  ["multidistrict_litigation", "Multidistrict litigation"],
  ["other_procedural_origin", "Other procedural origin"],
  ["social_security_review", "Social Security review"],
] as const;

const compactNumber = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("en-US");
const percent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 });
const signedPercent = new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1, signDisplay: "always" });

function FilingTrend({ explorer, filters }: { explorer: PopulationExplorer; filters: PopulationFilters }) {
  const target = useRef<HTMLDivElement>(null);
  const data = useMemo(() => selectFilingSeries(explorer, filters), [explorer, filters]);
  const series = explorer.dimensions.filing_years.map((year) => data.find((row) => row.filing_year === year));

  useEffect(() => {
    if (!target.current || data.length === 0) return;
    return mountChart(target.current, {
      animationDuration: chartAnimationDuration(),
      animationEasing: "cubicOut",
      grid: { left: 8, right: 18, top: 24, bottom: 8, containLabel: true },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: explorer.dimensions.filing_years.map(String),
        axisLabel: { color: "#667085", interval: 1, fontSize: 11 },
        axisLine: { lineStyle: { color: "#cfd6dc" } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#667085", formatter: (value: number) => compactNumber.format(value), fontSize: 11 },
        splitLine: { lineStyle: { color: "#e8ecef" } },
      },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number) => `${integer.format(value)} records`,
        backgroundColor: "#111b2b",
        borderWidth: 0,
        textStyle: { color: "#ffffff" },
      },
      series: [{
        type: "line",
        data: series.map((row) => row?.cohort_records ?? null),
        showSymbol: true,
        symbolSize: 6,
        smooth: 0.22,
        lineStyle: { color: "#167f85", width: 2.5 },
        itemStyle: { color: "#167f85", borderColor: "#ffffff", borderWidth: 2 },
        areaStyle: { color: "rgba(22, 127, 133, 0.10)" },
        connectNulls: false,
      }],
    });
  }, [data, explorer.dimensions.filing_years, series]);

  const summary = series.map((row, index) => (
    row ? `${explorer.dimensions.filing_years[index]}: ${integer.format(row.cohort_records)}` : `${explorer.dimensions.filing_years[index]}: withheld`
  )).join(", ");
  return <div ref={target} className="chart chart-wide" role="img" aria-label={`Filing volume by year. ${summary}`} />;
}

function PendingAge({ explorer, filters }: { explorer: PopulationExplorer; filters: PopulationFilters }) {
  const target = useRef<HTMLDivElement>(null);
  const data = useMemo(() => selectPendingAgeSeries(explorer, filters), [explorer, filters]);
  const series = explorer.dimensions.age_bands.map((band) => data.find((row) => row.age_band === band));

  useEffect(() => {
    if (!target.current || data.length === 0) return;
    return mountChart(target.current, {
      animationDuration: chartAnimationDuration(),
      animationEasing: "cubicOut",
      grid: { left: 6, right: 28, top: 10, bottom: 6, containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: { color: "#667085", formatter: (value: number) => compactNumber.format(value), fontSize: 11 },
        splitLine: { lineStyle: { color: "#e8ecef" } },
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: explorer.dimensions.age_bands.map(titleCase),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#344054", fontSize: 11 },
      },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number) => `${integer.format(value)} pending`,
        backgroundColor: "#111b2b",
        borderWidth: 0,
        textStyle: { color: "#ffffff" },
      },
      series: [{
        type: "bar",
        data: series.map((row, index) => ({
          value: row?.pending_records ?? null,
          itemStyle: { color: index === series.length - 1 ? "#c98224" : "#277f84" },
        })),
        barMaxWidth: 24,
        label: {
          show: true,
          position: "right",
          color: "#344054",
          formatter: ({ value }: { value: number }) => compactNumber.format(value),
        },
      }],
    });
  }, [data, explorer.dimensions.age_bands, series]);

  const summary = series.map((row, index) => (
    row ? `${titleCase(explorer.dimensions.age_bands[index])}: ${integer.format(row.pending_records)}` : `${titleCase(explorer.dimensions.age_bands[index])}: withheld`
  )).join(", ");
  return <div ref={target} className="chart chart-compact" role="img" aria-label={`Pending inventory by age. ${summary}`} />;
}

function CohortBenchmark({ benchmark }: { benchmark: Benchmark }) {
  const target = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!target.current) return;
    return mountChart(target.current, {
      animationDuration: chartAnimationDuration(),
      animationEasing: "cubicOut",
      grid: { left: 4, right: 40, top: 8, bottom: 4, containLabel: true },
      xAxis: {
        type: "value",
        min: 0,
        max: 1,
        axisLabel: { color: "#667085", formatter: (value: number) => `${Math.round(value * 100)}%`, fontSize: 11 },
        splitLine: { lineStyle: { color: "#e8ecef" } },
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: ["Within 365 days", "Within 730 days"],
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#344054", fontSize: 11 },
      },
      tooltip: { trigger: "axis", valueFormatter: (value: number) => percent.format(value) },
      series: [{
        type: "bar",
        data: [benchmark.termination_365_day_share, benchmark.termination_730_day_share],
        barMaxWidth: 24,
        itemStyle: { color: "#455a77" },
        label: { show: true, position: "right", color: "#344054", formatter: ({ value }: { value: number }) => percent.format(value) },
      }],
    });
  }, [benchmark]);

  return (
    <div
      ref={target}
      className="chart chart-benchmark"
      role="img"
      aria-label={`${percent.format(benchmark.termination_365_day_share)} terminated within 365 days and ${percent.format(benchmark.termination_730_day_share)} within 730 days among ${integer.format(benchmark.cases)} observed cases.`}
    />
  );
}

export type RankingMode = "district" | "nature";

type AnalyticsDashboardProps = {
  readiness: Readiness;
  portfolio: Portfolio;
  explorer: PopulationExplorer;
  benchmark: Benchmark;
  milestones: Milestones;
  provenance: Provenance;
  filters: PopulationFilters;
  cohort: string;
  rankingMode: RankingMode;
  onFiltersChange: (filters: PopulationFilters) => void;
  onCohortChange: (cohort: string) => void;
  onRankingModeChange: (mode: RankingMode) => void;
  onOpenScenario: () => void;
};

export function AnalyticsDashboard({
  readiness,
  portfolio,
  explorer,
  benchmark,
  milestones,
  provenance,
  filters,
  cohort,
  rankingMode,
  onFiltersChange,
  onCohortChange,
  onRankingModeChange,
  onOpenScenario,
}: AnalyticsDashboardProps) {
  const [scopeExpanded, setScopeExpanded] = useState(false);
  const slice = useMemo(() => selectPortfolioSlice(explorer, filters), [explorer, filters]);
  const pendingAge = useMemo(() => selectPendingAgeSeries(explorer, filters), [explorer, filters]);
  const filingChange = useMemo(() => selectLatestCompleteFilingChange(explorer, filters), [explorer, filters]);
  const districtRanking = useMemo(() => selectDistrictRanking(explorer, filters.natureFamily), [explorer, filters.natureFamily]);
  const natureRanking = useMemo(() => selectNatureRanking(explorer, filters.districtCode), [explorer, filters.districtCode]);
  const ranking = rankingMode === "district" ? districtRanking : natureRanking;
  const district = explorer.dimensions.districts.find((item) => item.district_code === filters.districtCode);
  const scope = [
    district ? `${district.ao_label} district` : "All 94 districts",
    filters.natureFamily === "all" ? "All case families" : titleCase(filters.natureFamily),
  ].join(" / ");
  const oldestPending = pendingAge.find((row) => row.age_band === "5_years_or_more");
  const oldestShare = slice && oldestPending && slice.pending_records > 0 ? oldestPending.pending_records / slice.pending_records : null;
  const nationalPendingShare = portfolio.pending_share;
  const pendingDifference = slice ? slice.pending_share - nationalPendingShare : 0;
  const rankingScope = rankingMode === "district"
    ? (filters.natureFamily === "all" ? "All case families" : titleCase(filters.natureFamily))
    : (district ? `${district.ao_label} district` : "Nationwide");

  function updateFilter(name: keyof PopulationFilters, value: string) {
    onFiltersChange({ ...filters, [name]: value });
  }

  function selectRank(key: string) {
    if (rankingMode === "district") updateFilter("districtCode", key);
    else updateFilter("natureFamily", key);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelector("#overview")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
  }

  return (
    <div className="dashboard" id="overview">
      <section className="dashboard-heading" aria-labelledby="dashboard-title">
        <div>
          <h1 id="dashboard-title">Federal civil portfolio intelligence</h1>
          <p>Observed workload, inventory pressure, cohort behavior, and evidence coverage across the complete governed population.</p>
        </div>
        <div className="snapshot-block">
          <span>Data snapshot</span>
          <strong>{explorer.source_snapshot}</strong>
          <small>2010 onward / public aggregate evidence</small>
        </div>
      </section>

      <section className={`query-bar${scopeExpanded ? " expanded" : ""}`} aria-label="Global dashboard scope">
        <div className="query-title">
          <span>Active analytical scope</span>
          <strong>{scope}</strong>
        </div>
        <button className="mobile-scope-toggle" type="button" aria-expanded={scopeExpanded} onClick={() => setScopeExpanded((value) => !value)}>{scopeExpanded ? "Close filters" : "Filters"}</button>
        <label>
          District
          <select value={filters.districtCode} onChange={(event) => updateFilter("districtCode", event.target.value)}>
            <option value="all">All 94 districts</option>
            {explorer.dimensions.districts.map((item) => (
              <option value={item.district_code} key={item.district_code}>{item.ao_label} / {item.court_id.toUpperCase()}</option>
            ))}
          </select>
        </label>
        <label>
          Case family
          <select value={filters.natureFamily} onChange={(event) => updateFilter("natureFamily", event.target.value)}>
            <option value="all">All 14 families</option>
            {explorer.dimensions.nature_families.map((item) => <option value={item} key={item}>{titleCase(item)}</option>)}
          </select>
        </label>
        <div className="filing-contract" aria-label="Filing period, fixed by data contract">
          <span>Filing period</span>
          <strong>2010 to 2026 snapshot</strong>
        </div>
        <label>
          Cohort context
          <select value={cohort} onChange={(event) => onCohortChange(event.target.value)}>
            {cohorts.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
        </label>
        <div className="query-actions">
          <button className="button-secondary" type="button" onClick={() => onFiltersChange({ districtCode: "all", natureFamily: "all" })} disabled={filters.districtCode === "all" && filters.natureFamily === "all"}>Clear</button>
        </div>
      </section>

      <p className="visually-hidden" aria-live="polite">
        {slice ? `${scope}: ${integer.format(slice.total_records)} records and ${integer.format(slice.pending_records)} pending.` : `${scope}: withheld below ${integer.format(explorer.publication_policy.minimum_support)} records.`}
      </p>

      {!slice ? (
        <section className="withheld-state" role="status">
          <div><strong>Selected intersection is withheld</strong><span>Publication threshold: {integer.format(explorer.publication_policy.minimum_support)} records</span></div>
          <p>This district and case-family intersection is below the safe aggregate support threshold. Broaden either filter to restore analytical measures.</p>
        </section>
      ) : (
        <>
          <section className="metric-strip" aria-label={`${scope} summary measures`}>
            <article><span>Statistical records</span><strong>{integer.format(slice.total_records)}</strong><small>{percent.format(slice.total_records / portfolio.statistical_records)} of nationwide records</small></article>
            <article><span>Pending inventory</span><strong>{integer.format(slice.pending_records)}</strong><small>{percent.format(slice.pending_share)} of selected records</small></article>
            <article><span>Matched evidence coverage</span><strong>{percent.format(slice.match_coverage)}</strong><small>{integer.format(slice.matched_records)} reviewed matches / all selected records</small></article>
            <article><span>Latest complete filing year</span><strong>{filingChange ? signedPercent.format(filingChange.change) : "Not available"}</strong><small>{filingChange ? `${filingChange.currentYear} compared with ${filingChange.previousYear}` : "Two supported years required"}</small></article>
          </section>

          <section className="scope-brief" aria-label="Scope interpretation">
            <div>
              <span>Portfolio signal</span>
              <strong>{Math.abs(pendingDifference) < 0.005 ? "Pending share is close to the nationwide rate." : `Pending share is ${Math.abs(pendingDifference * 100).toFixed(1)} points ${pendingDifference > 0 ? "above" : "below"} nationwide.`}</strong>
            </div>
            <dl>
              <div><dt>Five years or older / selected pending</dt><dd>{oldestShare === null ? "Withheld" : percent.format(oldestShare)}</dd></div>
              <div><dt>Observed terminations</dt><dd>{slice.observed_terminations === null ? "Withheld" : integer.format(slice.observed_terminations)}</dd></div>
              <div><dt>Observed mean duration</dt><dd>{slice.average_observed_duration_days === null ? "Withheld" : `${Math.round(slice.average_observed_duration_days)} days`}</dd></div>
            </dl>
          </section>

          <div className="analytics-grid" id="workload">
            <section className="analysis-panel trend-panel" aria-labelledby="trend-title">
              <div className="panel-heading">
                <div><h2 id="trend-title">Filing volume</h2><p>Annual filing cohorts for the active scope. The 2026 point is partial through {explorer.source_snapshot}.</p></div>
                <span>{selectFilingSeries(explorer, filters).length}/{explorer.dimensions.filing_years.length} years published</span>
              </div>
              <FilingTrend explorer={explorer} filters={filters} />
            </section>

            <section className="analysis-panel ranking-panel" aria-labelledby="ranking-title">
              <div className="panel-heading ranking-heading">
                <div><h2 id="ranking-title">Workload concentration</h2><p>Ranked by pending inventory within {rankingScope}.</p></div>
                <div className="segmented-control" aria-label="Ranking dimension">
                  <button type="button" aria-pressed={rankingMode === "district"} onClick={() => onRankingModeChange("district")}>Districts</button>
                  <button type="button" aria-pressed={rankingMode === "nature"} onClick={() => onRankingModeChange("nature")}>Case families</button>
                </div>
              </div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th scope="col">Rank</th><th scope="col">{rankingMode === "district" ? "District" : "Case family"}</th><th scope="col">Records</th><th scope="col">Pending</th><th scope="col">Pending share</th></tr></thead>
                  <tbody>
                    {ranking.slice(0, 8).map((row, index) => (
                      <tr key={row.key} className={row.key === (rankingMode === "district" ? filters.districtCode : filters.natureFamily) ? "selected-row" : ""}>
                        <td>{index + 1}</td>
                        <th scope="row"><button className="rank-link" type="button" onClick={() => selectRank(row.key)}>{row.label}</button></th>
                        <td>{integer.format(row.total_records)}</td>
                        <td>{integer.format(row.pending_records)}</td>
                        <td>{percent.format(row.pending_share)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="panel-footnote">Select a row to apply it to the global scope. Only published cells are ranked.</p>
            </section>

            <section className="analysis-panel" id="aging" aria-labelledby="aging-title">
              <div className="panel-heading"><div><h2 id="aging-title">Pending inventory age</h2><p>Open records are right-censored. Amber identifies the oldest published band.</p></div><span>{pendingAge.length}/{explorer.dimensions.age_bands.length} bands published</span></div>
              {pendingAge.length > 0 ? <PendingAge explorer={explorer} filters={filters} /> : <p className="inline-empty">No pending-age bands meet the publication threshold.</p>}
            </section>

            <section className="analysis-panel" id="cohorts" aria-labelledby="cohort-title">
              <div className="panel-heading"><div><h2 id="cohort-title">Historical cohort context</h2><p>{titleCase(benchmark.cohort)} cases with administratively mature observed outcomes.</p></div><span>{integer.format(benchmark.cases)} cases</span></div>
              <CohortBenchmark benchmark={benchmark} />
              <div className="cohort-meta"><span>Outcomes through {benchmark.outcomes_through}</span><span>{percent.format(benchmark.snapshot_censored_share)} snapshot censored</span></div>
              <p className="panel-footnote">{benchmark.limitation}</p>
            </section>
          </div>
        </>
      )}

      <section className="evidence-section" id="quality" aria-labelledby="quality-title">
        <div className="evidence-heading">
          <div><h2 id="quality-title">Evidence and capability status</h2><p>The interface distinguishes what the data supports from what remains unavailable.</p></div>
          <button className="button-secondary" type="button" onClick={onOpenScenario}>Open scenario lab</button>
        </div>
        <div className="evidence-grid">
          <article>
            <span className="status-label ready">Available</span>
            <h3>Observed portfolio analytics</h3>
            <strong>{integer.format(explorer.population.statistical_records)} records</strong>
            <p>Exact national and marginal totals with thresholded district-by-family intersections.</p>
          </article>
          <article>
            <span className="status-label ready">Available</span>
            <h3>Synthetic resource sensitivity</h3>
            <strong>{readiness.scenario_engine}</strong>
            <p>User assumptions produce deterministic low, base, and high staffing and budget cases.</p>
          </article>
          <article>
            <span className="status-label unavailable">Unavailable</span>
            <h3>Duration prediction</h3>
            <strong>Failed, not promoted</strong>
            <p>{readiness.reason}</p>
          </article>
          <article>
            <span className="status-label unavailable">Unavailable</span>
            <h3>Docket-event enrichment</h3>
            <strong>{percent.format(milestones.match_coverage)} match coverage</strong>
            <p>Missing {milestones.missing_event_fields.join(" and ")}. No event is inferred.</p>
          </article>
        </div>
      </section>

      <details className="methodology" id="methods">
        <summary><span>Methods, provenance, and publication contract</span><small>Release contract v{provenance.release_version}</small></summary>
        <div className="methodology-grid">
          <div><h3>Publication boundary</h3><p>{explorer.publication_policy.limitation}</p><dl><div><dt>Minimum support</dt><dd>{integer.format(explorer.publication_policy.minimum_support)}</dd></div><div><dt>Matter-level rows</dt><dd>{explorer.publication_policy.matter_level_rows}</dd></div><div><dt>Full population used</dt><dd>Yes</dd></div></dl></div>
          <div><h3>Source lineage</h3><dl><div><dt>FJC snapshot</dt><dd>{provenance.fjc_snapshot}</dd></div><div><dt>RECAP snapshot</dt><dd>{provenance.recap_snapshot}</dd></div><div><dt>Development outcomes</dt><dd>{provenance.development_outcomes_end}</dd></div></dl></div>
          <div><h3>Interpretation limits</h3><p>{portfolio.interpretation}</p><dl><div><dt>Legal advice</dt><dd>No</dd></div><div><dt>Observed cost forecast</dt><dd>No</dd></div><div><dt>Model status</dt><dd>Failed, not promoted</dd></div></dl></div>
        </div>
      </details>
    </div>
  );
}
