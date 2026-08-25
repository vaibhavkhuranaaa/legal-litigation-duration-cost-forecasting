import { type FormEvent, useEffect, useState } from "react";

import { AnalyticsDashboard, type RankingMode } from "./AnalyticsDashboard";
import {
  api,
  type Benchmark,
  type PopulationExplorer,
  type Portfolio,
  type Provenance,
  type Scenario,
} from "./api";
import {
  type PopulationFilters,
  selectFilingSeries,
  selectPendingAgeSeries,
  selectPortfolioSlice,
} from "./population";

const cohortOptions = [
  "ordinary_original",
  "multidistrict_litigation",
  "other_procedural_origin",
  "social_security_review",
];

type Workspace = "dashboard" | "scenario";
type NavigationSection = "overview" | "workload" | "aging" | "cohorts" | "scenario" | "methods";

const initialParameters = new URLSearchParams(window.location.search);
const initialWorkspace: Workspace = ["planner", "scenario"].includes(initialParameters.get("view") ?? "") ? "scenario" : "dashboard";
const initialCohort = cohortOptions.includes(initialParameters.get("cohort") ?? "")
  ? initialParameters.get("cohort") ?? "ordinary_original"
  : "ordinary_original";
const initialPopulationFilters: PopulationFilters = {
  districtCode: initialParameters.get("district") ?? "all",
  natureFamily: initialParameters.get("nature") ?? "all",
};
const initialRankingMode: RankingMode = initialParameters.get("rank") === "nature" ? "nature" : "district";

const integer = new Intl.NumberFormat("en-US");
const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function ScenarioWorkbench({ onBack }: { onBack: () => void }) {
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
    <div className="scenario-lab">
      <section className="scenario-heading">
        <div>
          <button className="text-action" type="button" onClick={onBack}>Back to portfolio dashboard</button>
          <h1>Synthetic resource sensitivity</h1>
          <p>Compare low, base, and high staffing cases from explicit workload, effort, and rate assumptions.</p>
        </div>
        <div className="scenario-boundary"><span>Calculation</span><strong>Synthetic assumptions</strong><small>Deterministic sensitivity</small></div>
      </section>

      <div className="scenario-layout">
        <section className="scenario-inputs" aria-labelledby="scenario-input-title">
          <div className="panel-heading"><div><h2 id="scenario-input-title">Assumptions</h2><p>All values are bounded by the release contract.</p></div></div>
          <form onSubmit={submit}>
            <label>Matters<input name="matters" type="number" min="1" max="10000" defaultValue="25" required /></label>
            <label>Planning horizon, months<input name="horizon_months" type="number" min="1" max="60" defaultValue="12" required /></label>
            <label>Attorney hours per matter-month<input name="attorney_hours_per_matter_month" type="number" min="0" max="500" step="0.5" defaultValue="4" required /></label>
            <label>Paralegal hours per matter-month<input name="paralegal_hours_per_matter_month" type="number" min="0" max="500" step="0.5" defaultValue="6" required /></label>
            <label>Synthetic attorney rate, USD<input name="attorney_rate_usd" type="number" min="0" max="5000" defaultValue="350" required /></label>
            <label>Synthetic paralegal rate, USD<input name="paralegal_rate_usd" type="number" min="0" max="5000" defaultValue="150" required /></label>
            <button className="button-primary scenario-submit" type="submit" disabled={pending}>{pending ? "Calculating sensitivity" : "Calculate sensitivity"}</button>
          </form>
          {error && <p className="inline-error" role="alert">{error}. Verify the API and try again.</p>}
        </section>

        <section className="scenario-output" aria-labelledby="scenario-output-title">
          <div className="panel-heading"><div><h2 id="scenario-output-title">Sensitivity cases</h2><p>Base assumptions are multiplied by 0.80, 1.00, and 1.25.</p></div><span>Productive capacity: 120 hours per FTE-month</span></div>
          {!scenario && !error && (
            <div className="scenario-empty">
              <strong>Ready for assumptions</strong>
              <p>Calculate once to compare staffing capacity and synthetic budget exposure across all three cases.</p>
            </div>
          )}
          {scenario && (
            <div className="scenario-results" aria-live="polite">
              <div className="table-wrap"><table>
                <thead><tr><th scope="col">Case</th><th scope="col">Attorney FTE</th><th scope="col">Paralegal FTE</th><th scope="col">Attorney hours</th><th scope="col">Paralegal hours</th><th scope="col">Synthetic budget</th></tr></thead>
                <tbody>{scenario.cases.map((item) => (
                  <tr key={item.name} className={item.name === "base" ? "selected-row" : ""}>
                    <th scope="row">{item.name}</th>
                    <td>{item.attorney_fte.toFixed(2)}</td>
                    <td>{item.paralegal_fte.toFixed(2)}</td>
                    <td>{integer.format(item.attorney_hours)}</td>
                    <td>{integer.format(item.paralegal_hours)}</td>
                    <td>{currency.format(item.budget_usd)}</td>
                  </tr>
                ))}</tbody>
              </table></div>
              <div className="scenario-summary">
                <div><span>Observed cost records</span><strong>0</strong></div>
                <div><span>Scenario method</span><strong>Deterministic</strong></div>
                <div><span>Data basis</span><strong>User assumptions</strong></div>
              </div>
              <p className="panel-footnote">{scenario.limitation}</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function App() {
  const [workspace, setWorkspace] = useState<Workspace>(initialWorkspace);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [explorer, setExplorer] = useState<PopulationExplorer | null>(null);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [provenance, setProvenance] = useState<Provenance | null>(null);
  const [cohort, setCohort] = useState(initialCohort);
  const [populationFilters, setPopulationFilters] = useState<PopulationFilters>(initialPopulationFilters);
  const [rankingMode, setRankingMode] = useState<RankingMode>(initialRankingMode);
  const [activeSection, setActiveSection] = useState<NavigationSection>(initialWorkspace === "scenario" ? "scenario" : "overview");
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);
  const [error, setError] = useState("");
  const [requestKey, setRequestKey] = useState(0);

  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([
      api.portfolio(), api.explorer(), api.benchmark(cohort), api.provenance(),
    ])
      .then(([nextPortfolio, nextExplorer, nextBenchmark, nextProvenance]) => {
        if (!active) return;
        setPortfolio(nextPortfolio);
        setExplorer(nextExplorer);
        setBenchmark(nextBenchmark);
        setProvenance(nextProvenance);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Data request failed");
      });
    return () => { active = false; };
  }, [cohort, requestKey]);

  useEffect(() => {
    if (!explorer) return;
    const districtValid = populationFilters.districtCode === "all" || explorer.dimensions.districts.some((item) => item.district_code === populationFilters.districtCode);
    const natureValid = populationFilters.natureFamily === "all" || explorer.dimensions.nature_families.includes(populationFilters.natureFamily);
    if (!districtValid || !natureValid) {
      setPopulationFilters({ districtCode: districtValid ? populationFilters.districtCode : "all", natureFamily: natureValid ? populationFilters.natureFamily : "all" });
    }
  }, [explorer, populationFilters]);

  useEffect(() => {
    const parameters = new URLSearchParams();
    if (workspace === "scenario") parameters.set("view", "scenario");
    if (populationFilters.districtCode !== "all") parameters.set("district", populationFilters.districtCode);
    if (populationFilters.natureFamily !== "all") parameters.set("nature", populationFilters.natureFamily);
    if (cohort !== "ordinary_original") parameters.set("cohort", cohort);
    if (rankingMode === "nature") parameters.set("rank", "nature");
    const query = parameters.toString();
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  }, [cohort, populationFilters, rankingMode, workspace]);

  function exportView() {
    const selectedSlice = explorer ? selectPortfolioSlice(explorer, populationFilters) : undefined;
    const selectedFilings = explorer ? selectFilingSeries(explorer, populationFilters) : [];
    const selectedPendingAge = explorer ? selectPendingAgeSeries(explorer, populationFilters) : [];
    const blob = new Blob([JSON.stringify({
      dashboard_contract: "enterprise-analytics-v1",
      schema_version: explorer?.schema_version,
      source_snapshot: explorer?.source_snapshot,
      filters: populationFilters,
      cohort,
      ranking_dimension: rankingMode,
      portfolio,
      selected_slice: selectedSlice,
      filing_series: selectedFilings,
      pending_age_series: selectedPendingAge,
      benchmark,
      provenance,
      publication_policy: explorer?.publication_policy,
    }, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "federal-civil-portfolio-view.json";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function openSection(id: string) {
    setWorkspace("dashboard");
    setActiveSection(id as NavigationSection);
    setMobileMoreOpen(false);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" }), 0);
  }

  function openScenario() {
    setWorkspace("scenario");
    setActiveSection("scenario");
    setMobileMoreOpen(false);
  }

  if (error) {
    return <main className="fatal-state"><span>Connection error</span><h1>Portfolio evidence did not load</h1><p>{error}. Start the local API or refresh the static artifact, then retry.</p><button className="button-primary" type="button" onClick={() => setRequestKey((value) => value + 1)}>Retry data load</button></main>;
  }

  if (!portfolio || !explorer || !benchmark || !provenance) {
    return <main className="loading-state" aria-busy="true"><span className="loading-line" /><span className="loading-line wide" /><span className="loading-block" /><p>Loading governed portfolio evidence</p></main>;
  }

  return (
    <div className="enterprise-shell">
      <aside className="side-navigation">
        <div className="brand-block"><span className="brand-mark" aria-hidden="true">FC</span><div><strong>Federal Civil</strong><span>Portfolio Intelligence</span></div></div>
        <nav aria-label="Analytics navigation">
          <button type="button" className={activeSection === "overview" ? "active" : ""} aria-current={activeSection === "overview" ? "page" : undefined} onClick={() => openSection("overview")}><span>Overview</span><small>National scope</small></button>
          <button type="button" className={activeSection === "workload" ? "active" : ""} aria-current={activeSection === "workload" ? "page" : undefined} onClick={() => openSection("workload")}><span>Workload</span><small>Trend and rank</small></button>
          <button type="button" className={activeSection === "aging" ? "active" : ""} aria-current={activeSection === "aging" ? "page" : undefined} onClick={() => openSection("aging")}><span>Pending age</span><small>Inventory pressure</small></button>
          <button type="button" className={activeSection === "cohorts" ? "active" : ""} aria-current={activeSection === "cohorts" ? "page" : undefined} onClick={() => openSection("cohorts")}><span>Cohorts</span><small>Observed outcomes</small></button>
          <button className="mobile-more-trigger" type="button" aria-expanded={mobileMoreOpen} aria-controls="secondary-navigation" onClick={() => setMobileMoreOpen((value) => !value)}><span>More</span><small>More views</small></button>
          <div className={`nav-more${mobileMoreOpen ? " open" : ""}`} id="secondary-navigation">
            <button type="button" className={activeSection === "scenario" ? "active" : ""} aria-current={activeSection === "scenario" ? "page" : undefined} onClick={openScenario}><span>Scenario lab</span><small>Synthetic sensitivity</small></button>
            <button type="button" className={activeSection === "methods" ? "active" : ""} aria-current={activeSection === "methods" ? "page" : undefined} onClick={() => openSection("methods")}><span>Methods</span><small>Source and policy</small></button>
          </div>
        </nav>
        <div className="side-status"><span>Full-population view</span><small>Snapshot {explorer.source_snapshot}</small></div>
      </aside>

      <main className="product-workspace">
        <header className="workspace-bar">
          <div><strong>{workspace === "dashboard" ? "Condensed dashboard" : "Scenario lab"}</strong><span>5.0M records / governed aggregates</span></div>
          <div className="workspace-actions"><span className="release-state">Contract v{provenance.release_version}</span>{workspace === "dashboard" && <button className="button-secondary" type="button" onClick={exportView}>Export evidence</button>}</div>
        </header>

        {workspace === "dashboard" ? (
          <AnalyticsDashboard
            portfolio={portfolio}
            explorer={explorer}
            benchmark={benchmark}
            provenance={provenance}
            filters={populationFilters}
            cohort={cohort}
            rankingMode={rankingMode}
            onFiltersChange={setPopulationFilters}
            onCohortChange={setCohort}
            onRankingModeChange={setRankingMode}
          />
        ) : <ScenarioWorkbench onBack={() => openSection("overview")} />}
      </main>
    </div>
  );
}

export default App;
