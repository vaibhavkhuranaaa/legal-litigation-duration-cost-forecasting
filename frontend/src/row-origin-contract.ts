const EXPECTED_CONTRACT = "public-row-mart.v1";
const EXPECTED_DATASET = "fjc-civil-2026-03-31.v1";
const EXPECTED_SCHEMA = "1.0.0";
const EXPECTED_CUTOFF = "2026-03-31";
const EXPECTED_METRICS = "metrics.v1";
const EXPECTED_RECORDS = 5_008_334;
const EXPECTED_YEARS = Array.from({ length: 17 }, (_, index) => 2010 + index);
export const APP_VERSION = "2.0.0";

export type RowPartition = {
  path: string;
  filing_year: number;
  row_count: number;
  byte_size: number;
  sha256: string;
  dataset_version: string;
  schema_version: string;
};

export type RowManifest = {
  contract_id: string;
  manifest_version: number;
  dataset_version: string;
  schema_version: string;
  source_snapshot_cutoff: string;
  minimum_app_version: string;
  opaque_key_version: number;
  date_policy: string;
  null_policy: string;
  total_records: number;
  metric_registry_version: string;
  source_attribution: string;
  source_terms_url: string;
  courtlistener_attribution: string;
  courtlistener_terms_url: string;
  dataset_terms: string;
  partitions: RowPartition[];
};

function requiredText(value: unknown, field: string): asserts value is string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`Row manifest ${field} is missing`);
}

export function checkedBaseUrl(value: string): URL {
  const url = new URL(value.endsWith("/") ? value : `${value}/`);
  const loopback = url.protocol === "http:" && ["127.0.0.1", "localhost"].includes(url.hostname);
  if (url.protocol !== "https:" && !loopback) throw new Error("Row data origin must use HTTPS or loopback HTTP");
  if (url.username || url.password || url.search || url.hash) {
    throw new Error("Row data origin must not contain credentials, a query, or a fragment");
  }
  return url;
}

function versionParts(value: string): number[] {
  if (!/^\d+\.\d+\.\d+$/.test(value)) throw new Error("Row manifest application version is invalid");
  return value.split(".").map(Number);
}

export function validateManifest(value: unknown, appVersion = APP_VERSION): RowManifest {
  if (!value || typeof value !== "object") throw new Error("Row manifest is not an object");
  const manifest = value as RowManifest;
  if (manifest.contract_id !== EXPECTED_CONTRACT || manifest.manifest_version !== 1) {
    throw new Error("Row manifest contract is incompatible");
  }
  if (manifest.dataset_version !== EXPECTED_DATASET || manifest.schema_version !== EXPECTED_SCHEMA) {
    throw new Error("Row manifest dataset or schema is incompatible");
  }
  requiredText(manifest.minimum_app_version, "minimum_app_version");
  const minimumVersion = versionParts(manifest.minimum_app_version);
  const currentVersion = versionParts(appVersion);
  if (
    manifest.source_snapshot_cutoff !== EXPECTED_CUTOFF ||
    currentVersion[0] !== minimumVersion[0] ||
    currentVersion.some((part, index) => part !== minimumVersion[index]
      ? part < minimumVersion[index] && currentVersion.slice(0, index).every((value, prior) => value === minimumVersion[prior])
      : false)
  ) {
    throw new Error("Row manifest release boundary is incompatible");
  }
  if (manifest.opaque_key_version !== 1 || manifest.total_records !== EXPECTED_RECORDS) {
    throw new Error("Row manifest population or key policy does not reconcile");
  }
  if (manifest.metric_registry_version !== EXPECTED_METRICS) {
    throw new Error("Row manifest metric registry is incompatible");
  }
  for (const field of [
    "date_policy",
    "null_policy",
    "source_attribution",
    "source_terms_url",
    "courtlistener_attribution",
    "courtlistener_terms_url",
    "dataset_terms",
  ] as const) requiredText(manifest[field], field);
  for (const field of ["source_terms_url", "courtlistener_terms_url"] as const) {
    if (new URL(manifest[field]).protocol !== "https:") throw new Error(`Row manifest ${field} must use HTTPS`);
  }
  if (!Array.isArray(manifest.partitions) || manifest.partitions.length !== EXPECTED_YEARS.length) {
    throw new Error("Row manifest must declare 17 annual partitions");
  }
  const years = new Set<number>();
  const paths = new Set<string>();
  for (const partition of manifest.partitions) {
    if (!Number.isInteger(partition.filing_year) || !EXPECTED_YEARS.includes(partition.filing_year)) {
      throw new Error("Row manifest contains an invalid filing year");
    }
    if (years.has(partition.filing_year) || paths.has(partition.path)) {
      throw new Error("Row manifest contains a duplicate partition");
    }
    if (partition.path !== `filing_year=${partition.filing_year}/part-00000.parquet`) {
      throw new Error("Row manifest contains an invalid partition path");
    }
    if (!Number.isSafeInteger(partition.row_count) || partition.row_count <= 0 ||
      !Number.isSafeInteger(partition.byte_size) || partition.byte_size <= 0 ||
      !/^[a-f0-9]{64}$/.test(partition.sha256)) {
      throw new Error("Row manifest contains invalid partition integrity metadata");
    }
    if (partition.dataset_version !== EXPECTED_DATASET || partition.schema_version !== EXPECTED_SCHEMA) {
      throw new Error("Row manifest contains an incompatible partition");
    }
    years.add(partition.filing_year);
    paths.add(partition.path);
  }
  if (EXPECTED_YEARS.some((year) => !years.has(year)) ||
    manifest.partitions.reduce((sum, partition) => sum + partition.row_count, 0) !== EXPECTED_RECORDS) {
    throw new Error("Row manifest partition population does not reconcile");
  }
  return manifest;
}

export function validateManifestResponse(response: Response, requestedUrl: URL): void {
  if (!response.ok) throw new Error(`Row manifest request failed with HTTP ${response.status}`);
  if (response.url && response.url !== requestedUrl.toString()) throw new Error("Row manifest redirected unexpectedly");
  if (!response.headers.get("content-type")?.toLowerCase().startsWith("application/json")) {
    throw new Error("Row manifest response has an incompatible content type");
  }
}

export function validatePartitionResponse(response: Response, requestedUrl: URL, partition: RowPartition): void {
  if (response.status !== 206) throw new Error("Row partition origin did not honor the byte-range contract");
  if (response.url && response.url !== requestedUrl.toString()) throw new Error("Row partition redirected unexpectedly");
  if (!response.headers.get("content-type")?.toLowerCase().startsWith("application/vnd.apache.parquet")) {
    throw new Error("Row partition response has an incompatible content type");
  }
  if (response.headers.get("accept-ranges")?.toLowerCase() !== "bytes") {
    throw new Error("Row partition origin does not advertise byte ranges");
  }
  const contentRange = response.headers.get("content-range");
  if (!contentRange || Number(contentRange.match(/\/(\d+)$/)?.[1]) !== partition.byte_size) {
    throw new Error("Row partition size does not match the manifest");
  }
  if (!response.headers.get("cache-control")?.toLowerCase().includes("immutable")) {
    throw new Error("Row partition origin does not provide immutable caching");
  }
}
