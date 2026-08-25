export type Readiness = {
  status: "ready";
  operations_analytics: "ready";
  duration_forecast: "unavailable";
  milestone_events: "unavailable";
  scenario_engine: "ready";
  reason: string;
};

export type Portfolio = {
  source_snapshot: string;
  statistical_records: number;
  pending_records: number;
  pending_share: number;
  collision_free_cases: number;
  promoted_recap_matches: number;
  recap_match_coverage: number;
  interpretation: string;
};

export type Benchmark = {
  status: "observed_benchmark";
  cohort: string;
  cases: number;
  termination_365_day_share: number;
  termination_730_day_share: number;
  snapshot_censored_share: number;
  outcomes_through: string;
  limitation: string;
};

export type Milestones = {
  status: "event_unavailable";
  event_updates_enabled: false;
  match_coverage: number;
  missing_event_fields: string[];
  fallback: string;
  limitation: string;
};

export type Provenance = {
  release_version: string;
  fjc_snapshot: string;
  recap_snapshot: string;
  development_outcomes_end: string;
  model_status: "failed_not_promoted";
  legal_advice: false;
  real_cost_forecast: false;
};

export type ScenarioCase = {
  name: string;
  multiplier: number;
  attorney_hours: number;
  paralegal_hours: number;
  attorney_fte: number;
  paralegal_fte: number;
  budget_usd: number;
};

export type Scenario = {
  scenario_type: "synthetic";
  observed_cost_data_used: false;
  assumptions: Record<string, number>;
  cases: ScenarioCase[];
  limitation: string;
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`Request failed with HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

const remoteApi = {
  readiness: () => request<Readiness>("/v1/readiness"),
  portfolio: () => request<Portfolio>("/v1/portfolio"),
  milestones: () => request<Milestones>("/v1/milestones/availability"),
  provenance: () => request<Provenance>("/v1/provenance"),
  benchmark: (cohort: string) =>
    request<Benchmark>("/v1/benchmarks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cohort }),
    }),
  scenario: (body: Record<string, number>) =>
    request<Scenario>("/v1/scenarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};

const cohorts: Record<string, [number, number, number, number]> = {
  ordinary_original: [2_503_909, 0.6679, 0.8456, 0.0165],
  multidistrict_litigation: [767_685, 0.232, 0.3748, 0.1578],
  other_procedural_origin: [551_610, 0.6984, 0.9046, 0.0109],
  social_security_review: [237_239, 0.4793, 0.9586, 0.0027],
};

const round = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100;

const staticApi = {
  readiness: async (): Promise<Readiness> => ({
    status: "ready",
    operations_analytics: "ready",
    duration_forecast: "unavailable",
    milestone_events: "unavailable",
    scenario_engine: "ready",
    reason: "M7 model gates failed; operations analytics and synthetic scenarios remain available.",
  }),
  portfolio: async (): Promise<Portfolio> => ({
    source_snapshot: "2026-03-31",
    statistical_records: 5_008_334,
    pending_records: 457_327,
    pending_share: 457_327 / 5_008_334,
    collision_free_cases: 4_645_719,
    promoted_recap_matches: 2_065_537,
    recap_match_coverage: 2_065_537 / 4_645_719,
    interpretation: "Observed nationwide public court metadata; not a duration forecast.",
  }),
  milestones: async (): Promise<Milestones> => ({
    status: "event_unavailable",
    event_updates_enabled: false,
    match_coverage: 2_065_537 / 4_645_719,
    missing_event_fields: ["entry_number", "description"],
    fallback: "observed_portfolio_and_cohort_context",
    limitation: "No docket event is inferred from fields that are not present.",
  }),
  provenance: async (): Promise<Provenance> => ({
    release_version: "1",
    fjc_snapshot: "2026-03-31",
    recap_snapshot: "2026-06-30",
    development_outcomes_end: "2024-03-31",
    model_status: "failed_not_promoted",
    legal_advice: false,
    real_cost_forecast: false,
  }),
  benchmark: async (cohort: string): Promise<Benchmark> => {
    const values = cohorts[cohort];
    if (!values) throw new Error("Unknown benchmark cohort");
    return {
      status: "observed_benchmark",
      cohort,
      cases: values[0],
      termination_365_day_share: values[1],
      termination_730_day_share: values[2],
      snapshot_censored_share: values[3],
      outcomes_through: "2024-03-31",
      limitation: "Historical cohort average; not a matter-specific prediction or legal advice.",
    };
  },
  scenario: async (body: Record<string, number>): Promise<Scenario> => {
    const assumptions = {
      ...body,
      productive_hours_per_fte_month: 120,
      low_multiplier: 0.8,
      high_multiplier: 1.25,
    };
    const attorneyHours = body.matters * body.horizon_months * body.attorney_hours_per_matter_month;
    const paralegalHours = body.matters * body.horizon_months * body.paralegal_hours_per_matter_month;
    const baseCost = attorneyHours * body.attorney_rate_usd + paralegalHours * body.paralegal_rate_usd;
    const capacity = body.horizon_months * assumptions.productive_hours_per_fte_month;
    const createCase = (name: string, multiplier: number): ScenarioCase => ({
      name,
      multiplier,
      attorney_hours: attorneyHours * multiplier,
      paralegal_hours: paralegalHours * multiplier,
      attorney_fte: round((attorneyHours * multiplier) / capacity),
      paralegal_fte: round((paralegalHours * multiplier) / capacity),
      budget_usd: round(baseCost * multiplier),
    });
    return {
      scenario_type: "synthetic",
      observed_cost_data_used: false,
      assumptions,
      cases: [createCase("low", 0.8), createCase("base", 1), createCase("high", 1.25)],
      limitation: "User-supplied sensitivity scenario; not an observed bill or real cost forecast.",
    };
  },
};

export const api = import.meta.env.VITE_STATIC_DEMO === "true" ? staticApi : remoteApi;
