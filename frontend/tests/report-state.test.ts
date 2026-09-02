import assert from "node:assert/strict";
import test from "node:test";

import {
  defaultReportState,
  parseReportState,
  reportPages,
  reportUrl,
  serializeReportState,
  type ReportState,
} from "../src/report-state.ts";

test("declares exactly eight report destinations", () => {
  assert.equal(reportPages.length, 8);
  assert.equal(new Set(reportPages.map((page) => page.id)).size, 8);
});

test("round-trips every supported report-state field", () => {
  const state: ReportState = {
    report: "district-comparison",
    districtCode: "09",
    natureFamily: "civil_rights",
    cohort: "multidistrict_litigation",
    rankingMode: "nature",
    drillFrom: "executive",
  };
  assert.deepEqual(parseReportState(`?${serializeReportState(state)}`), state);
  assert.equal(
    reportUrl(state, "/legal-litigation-duration-cost-forecasting/"),
    "/legal-litigation-duration-cost-forecasting/?report=district-comparison&district=09&nature=civil_rights&cohort=multidistrict_litigation&rank=nature&drill=executive",
  );
});

test("normalizes incompatible URL values to safe defaults", () => {
  assert.deepEqual(
    parseReportState("?report=unknown&cohort=prediction&rank=amount&drill=executive"),
    defaultReportState,
  );
});

test("omits default state from the shareable URL", () => {
  assert.equal(serializeReportState(defaultReportState), "");
});
