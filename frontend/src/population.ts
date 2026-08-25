import type {
  FilingPoint,
  PendingAgePoint,
  PopulationExplorer,
  PortfolioSlice,
} from "./api";

export type PopulationFilters = {
  districtCode: string;
  natureFamily: string;
};

export type RankedSlice = PortfolioSlice & {
  key: string;
  label: string;
};

function dimension(value: string) {
  return value === "all" ? null : value;
}

export function selectPortfolioSlice(
  explorer: PopulationExplorer,
  filters: PopulationFilters,
): PortfolioSlice | undefined {
  const districtCode = dimension(filters.districtCode);
  const natureFamily = dimension(filters.natureFamily);
  return explorer.portfolio_slices.find(
    (row) => row.district_code === districtCode && row.nature_family === natureFamily,
  );
}

export function selectFilingSeries(
  explorer: PopulationExplorer,
  filters: PopulationFilters,
): FilingPoint[] {
  const districtCode = dimension(filters.districtCode);
  const natureFamily = dimension(filters.natureFamily);
  return explorer.filing_series.filter(
    (row) => row.district_code === districtCode && row.nature_family === natureFamily,
  );
}

export function selectPendingAgeSeries(
  explorer: PopulationExplorer,
  filters: PopulationFilters,
): PendingAgePoint[] {
  const districtCode = dimension(filters.districtCode);
  const natureFamily = dimension(filters.natureFamily);
  return explorer.pending_age_series.filter(
    (row) => row.district_code === districtCode && row.nature_family === natureFamily,
  );
}

export function selectDistrictRanking(
  explorer: PopulationExplorer,
  natureFamily: string,
): RankedSlice[] {
  const family = dimension(natureFamily);
  const districtLabels = new Map(
    explorer.dimensions.districts.map((district) => [
      district.district_code,
      `${district.ao_label} / ${district.court_id.toUpperCase()}`,
    ]),
  );
  return explorer.portfolio_slices
    .filter((row) => row.district_code !== null && row.nature_family === family)
    .map((row) => ({
      ...row,
      key: row.district_code ?? "",
      label: districtLabels.get(row.district_code ?? "") ?? row.district_code ?? "Unknown district",
    }))
    .sort((left, right) => right.pending_records - left.pending_records);
}

export function selectNatureRanking(
  explorer: PopulationExplorer,
  districtCode: string,
): RankedSlice[] {
  const district = dimension(districtCode);
  return explorer.portfolio_slices
    .filter((row) => row.district_code === district && row.nature_family !== null)
    .map((row) => ({
      ...row,
      key: row.nature_family ?? "",
      label: titleCase(row.nature_family ?? "Unknown family"),
    }))
    .sort((left, right) => right.pending_records - left.pending_records);
}

export function selectLatestCompleteFilingChange(
  explorer: PopulationExplorer,
  filters: PopulationFilters,
) {
  const snapshotYear = Number(explorer.source_snapshot.slice(0, 4));
  const series = selectFilingSeries(explorer, filters)
    .filter((row) => row.filing_year < snapshotYear)
    .sort((left, right) => left.filing_year - right.filing_year);
  const current = series.at(-1);
  const previous = series.at(-2);
  if (!current || !previous || previous.cohort_records === 0) return null;
  return {
    currentYear: current.filing_year,
    previousYear: previous.filing_year,
    change: (current.cohort_records - previous.cohort_records) / previous.cohort_records,
  };
}

export function titleCase(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
