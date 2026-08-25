import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { useEffect, useMemo, useRef } from "react";

import type { PopulationExplorer as PopulationExplorerData } from "./api";
import {
  type PopulationFilters,
  selectFilingSeries,
  selectPendingAgeSeries,
  selectPortfolioSlice,
  titleCase,
} from "./population";

echarts.use([BarChart, GridComponent, TooltipComponent, SVGRenderer]);

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatPercent(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

function FilingChart({ data, years }: { data: ReturnType<typeof selectFilingSeries>; years: number[] }) {
  const target = useRef<HTMLDivElement>(null);
  const series = years.map((year) => data.find((row) => row.filing_year === year));

  useEffect(() => {
    if (!target.current || data.length === 0) return;
    const chart = echarts.init(target.current, undefined, { renderer: "svg" });
    chart.setOption({
      animationDuration: 520,
      animationEasing: "cubicOut",
      grid: { left: 14, right: 10, top: 16, bottom: 12, containLabel: true },
      xAxis: {
        type: "category",
        data: years.map(String),
        axisLabel: { color: "#475569", interval: 1 },
        axisLine: { lineStyle: { color: "#aebac0" } },
        axisTick: { show: false },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#475569", formatter: (value: number) => Intl.NumberFormat("en-US", { notation: "compact" }).format(value) },
        splitLine: { lineStyle: { color: "#e3e8ea" } },
      },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number) => `${formatNumber(value)} filings`,
      },
      series: [{
        type: "bar",
        data: series.map((row) => row?.cohort_records ?? null),
        barMaxWidth: 28,
        itemStyle: { color: "#173b57", borderRadius: [3, 3, 0, 0] },
      }],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(target.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [data, series, years]);

  const summary = series
    .map((row, index) => row ? `${years[index]}: ${formatNumber(row.cohort_records)}` : `${years[index]}: withheld`)
    .join(", ");
  return <div ref={target} className="population-chart" role="img" aria-label={`Filing records by year. ${summary}`} />;
}

function PendingAgeChart({ data, ageBands }: { data: ReturnType<typeof selectPendingAgeSeries>; ageBands: string[] }) {
  const target = useRef<HTMLDivElement>(null);
  const series = ageBands.map((ageBand) => data.find((row) => row.age_band === ageBand));

  useEffect(() => {
    if (!target.current || data.length === 0) return;
    const chart = echarts.init(target.current, undefined, { renderer: "svg" });
    chart.setOption({
      animationDuration: 520,
      animationEasing: "cubicOut",
      grid: { left: 8, right: 20, top: 16, bottom: 8, containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: { color: "#475569", formatter: (value: number) => Intl.NumberFormat("en-US", { notation: "compact" }).format(value) },
        splitLine: { lineStyle: { color: "#e3e8ea" } },
      },
      yAxis: {
        type: "category",
        data: ageBands.map(titleCase),
        axisLabel: { color: "#17202a", fontWeight: 600 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value: number) => `${formatNumber(value)} pending`,
      },
      series: [{
        type: "bar",
        data: series.map((row) => row?.pending_records ?? null),
        barMaxWidth: 26,
        itemStyle: { color: "#087e8b", borderRadius: [0, 3, 3, 0] },
      }],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(target.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [ageBands, data, series]);

  const summary = series
    .map((row, index) => row ? `${titleCase(ageBands[index])}: ${formatNumber(row.pending_records)}` : `${titleCase(ageBands[index])}: withheld`)
    .join(", ");
  return <div ref={target} className="population-chart" role="img" aria-label={`Pending inventory by age. ${summary}`} />;
}

type PopulationExplorerProps = {
  explorer: PopulationExplorerData;
  filters: PopulationFilters;
  onFiltersChange: (filters: PopulationFilters) => void;
};

export function PopulationExplorer({ explorer, filters, onFiltersChange }: PopulationExplorerProps) {
  const slice = useMemo(() => selectPortfolioSlice(explorer, filters), [explorer, filters]);
  const filings = useMemo(() => selectFilingSeries(explorer, filters), [explorer, filters]);
  const pendingAge = useMemo(() => selectPendingAgeSeries(explorer, filters), [explorer, filters]);
  const district = explorer.dimensions.districts.find((item) => item.district_code === filters.districtCode);
  const scope = [district?.court_id.toUpperCase(), filters.natureFamily === "all" ? null : titleCase(filters.natureFamily)]
    .filter(Boolean)
    .join(" · ") || "Nationwide · all nature families";

  function update(name: keyof PopulationFilters, value: string) {
    onFiltersChange({ ...filters, [name]: value });
  }

  return (
    <section className="population-explorer" aria-labelledby="population-explorer-title">
      <p className="visually-hidden" aria-live="polite">
        {slice ? `${scope}: ${formatNumber(slice.total_records)} records, ${formatNumber(slice.pending_records)} pending.` : `${scope}: slice withheld below ${formatNumber(explorer.publication_policy.minimum_support)} records.`}
      </p>
      <div className="population-explorer-heading">
        <div>
          <p className="kicker observed">Full-population explorer</p>
          <h2 id="population-explorer-title">Interrogate all 5,008,334 governed records</h2>
          <p>Filter exact marginal totals and supported district-by-family slices. Filing and pending-aging views are computed from the complete warehouse population.</p>
        </div>
        <div className="population-proof">
          <strong>100%</strong>
          <span>of eligible records used</span>
          <small>0 matter-level rows published</small>
        </div>
      </div>

      <div className="population-filter-bar" aria-label="Population filters">
        <label>
          District
          <select value={filters.districtCode} onChange={(event) => update("districtCode", event.target.value)}>
            <option value="all">All 94 districts</option>
            {explorer.dimensions.districts.map((item) => (
              <option value={item.district_code} key={item.district_code}>{item.court_id.toUpperCase()} · code {item.district_code}</option>
            ))}
          </select>
        </label>
        <label>
          Nature family
          <select value={filters.natureFamily} onChange={(event) => update("natureFamily", event.target.value)}>
            <option value="all">All 14 families</option>
            {explorer.dimensions.nature_families.map((item) => <option value={item} key={item}>{titleCase(item)}</option>)}
          </select>
        </label>
        <button type="button" onClick={() => onFiltersChange({ districtCode: "all", natureFamily: "all" })} disabled={filters.districtCode === "all" && filters.natureFamily === "all"}>Reset filters</button>
        <div className="active-scope"><span>Active scope</span><strong>{scope}</strong></div>
      </div>

      {!slice ? (
        <div className="suppressed-state" role="status">
          <strong>Slice withheld below the publication threshold.</strong>
          <p>This district-by-family cell contains fewer than {formatNumber(explorer.publication_policy.minimum_support)} records. Choose a broader scope to recover the aggregate view.</p>
        </div>
      ) : (
        <>
          <div className="slice-metrics" aria-label={`${scope} measures`}>
            <div><span>Records</span><strong>{formatNumber(slice.total_records)}</strong><small>Observed filings since 2010</small></div>
            <div><span>Pending</span><strong>{formatNumber(slice.pending_records)}</strong><small>{formatPercent(slice.pending_share)} of selected records</small></div>
            <div><span>Reviewed match coverage</span><strong>{formatPercent(slice.match_coverage)}</strong><small>{formatNumber(slice.matched_records)} matches ÷ all selected records</small></div>
            <div><span>Observed duration</span><strong>{slice.average_observed_duration_days === null ? "Withheld" : `${Math.round(slice.average_observed_duration_days)} days`}</strong><small>{slice.observed_terminations === null ? "Support withheld" : `${formatNumber(slice.observed_terminations)} terminated cases`}, descriptive only</small></div>
          </div>

          <div className="population-chart-grid">
            <article>
              <div><h3>Filing volume by year</h3><p>{filings.length} of {explorer.dimensions.filing_years.length} annual cells published. 2026 is partial through {explorer.source_snapshot}; gaps are withheld.</p></div>
              {filings.length > 0 ? <FilingChart data={filings} years={explorer.dimensions.filing_years} /> : <p className="empty-state">No supported annual series for this slice.</p>}
            </article>
            <article>
              <div><h3>Pending inventory by age</h3><p>{pendingAge.length} of {explorer.dimensions.age_bands.length} age bands published. Open records are right-censored; gaps are withheld.</p></div>
              {pendingAge.length > 0 ? <PendingAgeChart data={pendingAge} ageBands={explorer.dimensions.age_bands} /> : <p className="empty-state">No supported pending-age series for this slice.</p>}
            </article>
          </div>
        </>
      )}

      <div className="population-method">
        <strong>Publication rule</strong>
        <p>{explorer.publication_policy.limitation}</p>
        <span>Minimum support {formatNumber(explorer.publication_policy.minimum_support)} · schema v{explorer.schema_version} · snapshot {explorer.source_snapshot}</span>
      </div>
    </section>
  );
}
