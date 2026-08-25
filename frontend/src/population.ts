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

export function titleCase(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
