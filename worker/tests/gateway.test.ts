import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";

import worker from "../src/index";

const prefix = env.RELEASE_PREFIX;
const candidateOrigin = env.CANDIDATE_ORIGIN;
const pagesOrigin = "https://vaibhavkhuranaaa.github.io";
const partitionPath = "row-data/fjc-civil-2026-03-31.v1/filing_year=2025/part-00000.parquet";

beforeEach(async () => {
  await env.DATA.put(`${prefix}/index.html`, "<!doctype html><title>Candidate</title>", {
    httpMetadata: { contentType: "text/html; charset=utf-8" },
  });
  await env.DATA.put(`${prefix}/${partitionPath}`, new TextEncoder().encode("PAR1-0123456789-PAR1"), {
    httpMetadata: { contentType: "application/vnd.apache.parquet" },
  });
  await env.DATA.put(`${prefix}/assets/duckdb-browser-eh.worker-D6ypKDsm.js`, "self.onmessage=()=>{}", {
    httpMetadata: { contentType: "text/javascript; charset=utf-8" },
  });
  await env.DATA.put(`${prefix}/assets/full-population.v1-Bywqab--.json`, JSON.stringify({
    population: { statistical_records: 5_008_334 },
    schema_version: "1",
  }), { httpMetadata: { contentType: "application/json; charset=utf-8" } });
});

describe("row data gateway", () => {
  it("streams an allowlisted asset with security headers", async () => {
    const response = await worker.fetch(new Request(`${candidateOrigin}/`), env);
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-cache");
    expect(response.headers.get("content-security-policy")).toContain("default-src 'none'");
    expect(await response.text()).toContain("Candidate");

    const shareable = await worker.fetch(new Request(
      `${candidateOrigin}/?report=record-explorer&district=09&nature=civil_rights`,
    ), env);
    expect(shareable.status).toBe(200);

    const duckdbWorker = await worker.fetch(new Request(
      `${candidateOrigin}/assets/duckdb-browser-eh.worker-D6ypKDsm.js`,
    ), env);
    expect(duckdbWorker.headers.get("cross-origin-embedder-policy")).toBe("require-corp");
  });

  it("honors GET and HEAD byte ranges with immutable Parquet metadata", async () => {
    for (const method of ["GET", "HEAD"]) {
      const response = await worker.fetch(new Request(`${candidateOrigin}/${partitionPath}`, {
        method,
        headers: { Origin: pagesOrigin, Range: "bytes=5-9" },
      }), env);
      expect(response.status).toBe(206);
      expect(response.headers.get("accept-ranges")).toBe("bytes");
      expect(response.headers.get("content-range")).toBe("bytes 5-9/20");
      expect(response.headers.get("content-length")).toBe("5");
      expect(response.headers.get("content-type")).toBe("application/vnd.apache.parquet");
      expect(response.headers.get("cache-control")).toContain("immutable");
      expect(response.headers.get("access-control-allow-origin")).toBe(pagesOrigin);
      if (method === "GET") expect(new TextDecoder().decode(await response.arrayBuffer())).toBe("01234");
      else expect(await response.text()).toBe("");
    }
  });

  it("permits only the frozen CORS preflight", async () => {
    const response = await worker.fetch(new Request(`${candidateOrigin}/${partitionPath}`, {
      method: "OPTIONS",
      headers: {
        Origin: pagesOrigin,
        "Access-Control-Request-Method": "HEAD",
        "Access-Control-Request-Headers": "Range",
      },
    }), env);
    expect(response.status).toBe(204);
    expect(response.headers.get("access-control-allow-origin")).toBe(pagesOrigin);
    expect(response.headers.get("access-control-allow-headers")).toBe("Range");
  });

  it("fails closed for foreign origins, query strings, paths, ranges, and writes", async () => {
    const cases: Array<[string, RequestInit | undefined, number]> = [
      [`${candidateOrigin}/${partitionPath}`, { headers: { Origin: "https://example.test" } }, 403],
      [`${candidateOrigin}/${partitionPath}?download=1`, undefined, 400],
      [`${candidateOrigin}/?report=record-explorer&report=executive`, undefined, 400],
      [`${candidateOrigin}/?unknown=value`, undefined, 400],
      [`${candidateOrigin}/private/source.parquet`, undefined, 404],
      [`${candidateOrigin}/${partitionPath}`, { headers: { Range: "bytes=0-1,3-4" } }, 416],
      [`${candidateOrigin}/${partitionPath}`, { method: "PUT", body: "no" }, 405],
    ];
    for (const [url, init, status] of cases) {
      expect((await worker.fetch(new Request(url, init), env)).status).toBe(status);
    }
  });

  it("serves the frozen aggregate compatibility API without enabling writes", async () => {
    const portfolio = await worker.fetch(new Request(`${candidateOrigin}/v1/portfolio`), env);
    expect(portfolio.status).toBe(200);
    expect((await portfolio.json() as { statistical_records: number }).statistical_records).toBe(5_008_334);

    const population = await worker.fetch(new Request(`${candidateOrigin}/v1/population-explorer`), env);
    expect(population.status).toBe(200);
    expect((await population.json() as { schema_version: string }).schema_version).toBe("1");

    const benchmark = await worker.fetch(new Request(`${candidateOrigin}/v1/benchmarks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cohort: "ordinary_original" }),
    }), env);
    expect(benchmark.status).toBe(200);
    expect((await benchmark.json() as { cases: number }).cases).toBe(2_503_909);

    expect((await worker.fetch(new Request(`${candidateOrigin}/v1/portfolio`, {
      method: "PUT",
      body: "no",
    }), env)).status).toBe(405);
  });
});
