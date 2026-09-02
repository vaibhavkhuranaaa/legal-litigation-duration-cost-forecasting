import assert from "node:assert/strict";
import test from "node:test";

import {
  checkedBaseUrl,
  validateManifest,
  validateManifestResponse,
  validatePartitionResponse,
} from "../src/row-origin-contract.ts";

const partition = {
  path: "filing_year=2010/part-00000.parquet",
  filing_year: 2010,
  row_count: 1,
  byte_size: 8,
  sha256: "a".repeat(64),
  dataset_version: "fjc-civil-2026-03-31.v1",
  schema_version: "1.0.0",
};

function response(status: number, headers: Record<string, string>, url = "") {
  const result = new Response(null, { status, headers });
  if (url) Object.defineProperty(result, "url", { value: url });
  return result;
}

test("accepts HTTPS and loopback origins without ambient URL state", () => {
  assert.equal(checkedBaseUrl("https://data.example/v1").href, "https://data.example/v1/");
  assert.equal(checkedBaseUrl("http://127.0.0.1:8765").href, "http://127.0.0.1:8765/");
  for (const value of ["http://data.example", "https://user@data.example", "https://data.example?q=1", "https://data.example/#x"]) {
    assert.throws(() => checkedBaseUrl(value));
  }
});

test("rejects incomplete and duplicate manifest contracts", () => {
  assert.throws(() => validateManifest({ contract_id: "public-row-mart.v1" }), /contract|dataset/);
  const years = Array.from({ length: 17 }, (_, index) => 2010 + index);
  const manifest = {
    contract_id: "public-row-mart.v1",
    manifest_version: 1,
    dataset_version: "fjc-civil-2026-03-31.v1",
    schema_version: "1.0.0",
    source_snapshot_cutoff: "2026-03-31",
    minimum_app_version: "2.0.0",
    opaque_key_version: 1,
    date_policy: "month policy",
    null_policy: "null policy",
    total_records: 5_008_334,
    metric_registry_version: "metrics.v1",
    source_attribution: "FJC",
    source_terms_url: "https://www.fjc.gov/research/idb",
    courtlistener_attribution: "CourtListener",
    courtlistener_terms_url: "https://wiki.free.law/terms",
    dataset_terms: "Preserve attribution",
    partitions: years.map((filingYear, index) => ({
      ...partition,
      filing_year: filingYear,
      path: `filing_year=${filingYear}/part-00000.parquet`,
      row_count: index === 0 ? 5_008_318 : 1,
      sha256: index.toString(16).padStart(64, "0"),
    })),
  };
  assert.equal(validateManifest(manifest).partitions.length, 17);
  assert.throws(() => validateManifest(manifest, "1.9.9"), /release boundary/);
  assert.throws(() => validateManifest(manifest, "2.0"), /application version/);
  assert.throws(() => validateManifest({ ...manifest, partitions: manifest.partitions.map((item) => ({ ...item, filing_year: 2010, path: "filing_year=2010/part-00000.parquet" })) }), /duplicate/);
});

test("fails closed on redirected or mistyped manifest responses", () => {
  const url = new URL("https://data.example/v1/manifest.json");
  validateManifestResponse(response(200, { "content-type": "application/json" }, url.href), url);
  assert.throws(() => validateManifestResponse(response(200, { "content-type": "text/html" }, url.href), url), /content type/);
  assert.throws(() => validateManifestResponse(response(200, { "content-type": "application/json" }, "https://other.example/manifest.json"), url), /redirected/);
});

test("requires range, type, size, and immutable cache guarantees", () => {
  const url = new URL("https://data.example/v1/filing_year=2010/part-00000.parquet");
  const headers = {
    "content-type": "application/vnd.apache.parquet",
    "accept-ranges": "bytes",
    "content-range": "bytes 0-7/8",
    "cache-control": "public, max-age=31536000, immutable",
  };
  validatePartitionResponse(response(206, headers, url.href), url, partition);
  assert.throws(() => validatePartitionResponse(response(200, headers, url.href), url, partition), /byte-range/);
  assert.throws(() => validatePartitionResponse(response(206, { ...headers, "content-range": "bytes 0-6/7" }, url.href), url, partition), /size/);
  assert.throws(() => validatePartitionResponse(response(206, { ...headers, "cache-control": "no-store" }, url.href), url, partition), /immutable/);
});
