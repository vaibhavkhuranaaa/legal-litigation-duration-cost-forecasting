import assert from "node:assert/strict";
import test from "node:test";

import {
  compileRecordCount,
  compileRecordDetail,
  compileRecordQuery,
  formulaSafeValue,
  normalizeRecordValue,
  recordExportProvenance,
  recordsToCsv,
  type RecordQuerySpec,
} from "../src/record-explorer.ts";

const spec: RecordQuerySpec = {
  columns: ["district_code", "duration_days"],
  districtCode: "12",
  natureFamily: "civil_rights",
  sortColumn: "duration_days",
  sortDirection: "desc",
  limit: 200,
  offset: 400,
};

test("compiles projected, parameterized, deterministic bounded queries", () => {
  const query = compileRecordQuery(spec);
  assert.equal(query.parameters.join("|"), "12|civil_rights|200|400");
  assert.match(query.sql, /^select "release_record_key", "district_code", "duration_days"/);
  assert.match(query.sql, /order by "duration_days" desc, "release_record_key" asc limit \? offset \?$/);
  assert.equal(query.sql.includes("12"), false);
});

test("compiles count queries from the same filter scope", () => {
  assert.deepEqual(compileRecordCount(spec), {
    sql: 'select count(*)::integer as matching_records from governed_records where "district_code" = ? and "nature_of_suit_family" = ?',
    parameters: ["12", "civil_rights"],
  });
});

test("compiles one parameterized all-approved-field detail lookup", () => {
  const detail = compileRecordDetail("R0DXKFit60iTTj57_bGtNA");
  assert.equal(detail.parameters[0], "R0DXKFit60iTTj57_bGtNA");
  assert.match(detail.sql, /where "release_record_key" = \? limit 1$/);
  assert.equal(detail.sql.includes("docket_number"), false);
  assert.throws(() => compileRecordDetail("unsafe' or 1=1"), /incompatible/);
});

test("rejects unbounded and unregistered query inputs", () => {
  assert.throws(() => compileRecordQuery({ ...spec, limit: 10_001 }), /limit/);
  assert.throws(() => compileRecordQuery({ ...spec, sortColumn: "docket_number" }), /Unsupported/);
  assert.throws(() => compileRecordQuery({ ...spec, columns: ["office_code"] }), /Unsupported/);
});

test("neutralizes spreadsheet formula prefixes", () => {
  for (const value of ["=1+1", "+cmd", "-2+3", "@SUM(A1:A2)", "  =1+1", "\t=1+1"]) {
    assert.equal(formulaSafeValue(value).startsWith("'"), true);
  }
  assert.equal(formulaSafeValue("ordinary_original"), "ordinary_original");
});

test("writes stable CRLF CSV with quoting and formula safety", () => {
  const csv = recordsToCsv([
    { release_record_key: "row-1", district_code: "12", nature_of_suit_family: "=unsafe" },
    { release_record_key: "row-2", district_code: "3L", nature_of_suit_family: 'tort, "other"' },
  ], ["district_code", "nature_of_suit_family"]);
  assert.equal(
    csv,
    'release_record_key,district_code,nature_of_suit_family\r\nrow-1,12,\'=unsafe\r\nrow-2,3L,"tort, ""other"""\r\n',
  );
});

test("normalizes Arrow date millisecond values as public month strings", () => {
  assert.equal(normalizeRecordValue(1_764_547_200_000, "filed_month"), "2025-12-01");
  assert.equal(normalizeRecordValue(105, "duration_days"), 105);
});

test("builds deterministic export provenance from the exact query scope", () => {
  const provenance = recordExportProvenance({
    contract_id: "public-row-mart.v1",
    dataset_version: "fjc-civil-2026-03-31.v1",
    schema_version: "public-row.v1",
    metric_registry_version: "metrics.v1",
    source_snapshot_cutoff: "2026-03-31",
    source_attribution: "FJC",
    courtlistener_attribution: "CourtListener",
    dataset_terms: "Preserve attribution.",
  }, spec, 2025, "parquet", 1_710);
  assert.deepEqual(provenance.projected_columns, ["release_record_key", "district_code", "duration_days"]);
  assert.equal(provenance.exported_rows, 1_710);
  assert.equal(provenance.row_limit, 10_000);
  assert.equal(provenance.format, "parquet");
  assert.equal("generated_at" in provenance, false);
});
