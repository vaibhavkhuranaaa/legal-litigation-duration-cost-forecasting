export const reportPages = [
  { id: "executive", label: "Executive overview", shortLabel: "Overview", description: "National scope" },
  { id: "filing-trends", label: "Filing trends", shortLabel: "Filings", description: "Volume and change" },
  { id: "pending-aging", label: "Pending inventory and aging", shortLabel: "Pending", description: "Inventory pressure" },
  { id: "case-mix", label: "Case mix", shortLabel: "Case mix", description: "Nature composition" },
  { id: "district-comparison", label: "District comparison", shortLabel: "Districts", description: "Workload comparison" },
  { id: "record-explorer", label: "Record explorer", shortLabel: "Records", description: "Bounded row evidence" },
  { id: "data-quality", label: "Data quality and coverage", shortLabel: "Quality", description: "Support and lineage" },
  { id: "scenario-methods", label: "Scenario lab and methods", shortLabel: "Scenario", description: "Synthetic planning" },
] as const;

export type ReportId = (typeof reportPages)[number]["id"];
export type RankingMode = "district" | "nature";

export type ReportState = {
  report: ReportId;
  districtCode: string;
  natureFamily: string;
  cohort: string;
  rankingMode: RankingMode;
  drillFrom?: ReportId;
};

export const cohortIds = [
  "ordinary_original",
  "multidistrict_litigation",
  "other_procedural_origin",
  "social_security_review",
] as const;

export const defaultReportState: ReportState = {
  report: "executive",
  districtCode: "all",
  natureFamily: "all",
  cohort: "ordinary_original",
  rankingMode: "district",
};

const reportIds = new Set<string>(reportPages.map((page) => page.id));
const cohorts = new Set<string>(cohortIds);

function reportId(value: string | null): ReportId | undefined {
  return value && reportIds.has(value) ? value as ReportId : undefined;
}

export function parseReportState(search: string): ReportState {
  const parameters = new URLSearchParams(search);
  const report = reportId(parameters.get("report")) ?? defaultReportState.report;
  const drillFrom = reportId(parameters.get("drill"));
  return {
    report,
    districtCode: parameters.get("district") || "all",
    natureFamily: parameters.get("nature") || "all",
    cohort: cohorts.has(parameters.get("cohort") ?? "")
      ? parameters.get("cohort") ?? defaultReportState.cohort
      : defaultReportState.cohort,
    rankingMode: parameters.get("rank") === "nature" ? "nature" : "district",
    ...(drillFrom && drillFrom !== report ? { drillFrom } : {}),
  };
}

export function serializeReportState(state: ReportState): string {
  const parameters = new URLSearchParams();
  if (state.report !== defaultReportState.report) parameters.set("report", state.report);
  if (state.districtCode !== "all") parameters.set("district", state.districtCode);
  if (state.natureFamily !== "all") parameters.set("nature", state.natureFamily);
  if (state.cohort !== defaultReportState.cohort) parameters.set("cohort", state.cohort);
  if (state.rankingMode !== defaultReportState.rankingMode) parameters.set("rank", state.rankingMode);
  if (state.drillFrom && state.drillFrom !== state.report) parameters.set("drill", state.drillFrom);
  return parameters.toString();
}

export function reportUrl(state: ReportState, pathname: string): string {
  const query = serializeReportState(state);
  return `${pathname}${query ? `?${query}` : ""}`;
}

export function reportLabel(report: ReportId): string {
  return reportPages.find((page) => page.id === report)?.label ?? report;
}
