import { env } from "cloudflare:workers";
import { describe, expect, it } from "vitest";

import worker from "../src/upload";

const origin = "https://legal-litigation-row-candidate.gp-access-planner.workers.dev";
const prefix = "releases/m22-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const uploadEnv = Object.assign(env, { RELEASE_PREFIX: prefix, UPLOAD_TOKEN: "test-token" });

describe("one-time candidate uploader", () => {
  it("stores an allowlisted object with immutable metadata", async () => {
    const body = new TextEncoder().encode("PAR1-test-PAR1");
    const path = "row-data/fjc-civil-2026-03-31.v1/filing_year=2025/part-00000.parquet";
    const response = await worker.fetch(new Request(`${origin}/__m22-upload/${path}`, {
      method: "PUT",
      headers: {
        Authorization: "Bearer test-token",
        "Content-Length": String(body.byteLength),
      },
      body,
    }), uploadEnv);
    expect(response.status).toBe(201);
    const stored = await env.DATA.get(`${prefix}/${path}`);
    expect(await stored?.text()).toBe("PAR1-test-PAR1");
    expect(stored?.httpMetadata?.contentType).toBe("application/vnd.apache.parquet");
    expect(stored?.httpMetadata?.cacheControl).toContain("immutable");
  });

  it("fails closed for missing auth, paths, methods, and oversized bodies", async () => {
    const validPath = `${origin}/__m22-upload/index.html`;
    const cases: Request[] = [
      new Request(validPath, { method: "PUT", headers: { "Content-Length": "1" }, body: "x" }),
      new Request(`${origin}/__m22-upload/private/source.csv`, {
        method: "PUT",
        headers: { Authorization: "Bearer test-token", "Content-Length": "1" },
        body: "x",
      }),
      new Request(validPath),
      new Request(validPath, {
        method: "PUT",
        headers: { Authorization: "Bearer test-token", "Content-Length": String(65 * 1024 * 1024) },
        body: "x",
      }),
    ];
    for (const request of cases) {
      expect((await worker.fetch(request, uploadEnv)).status).not.toBe(201);
    }
  });

  it("completes authenticated multipart uploads", async () => {
    const path = "assets/duckdb-test.wasm";
    const headers = { Authorization: "Bearer test-token" };
    const started = await worker.fetch(new Request(`${origin}/__m22-multipart/start/${path}`, {
      method: "POST",
      headers,
    }), uploadEnv);
    expect(started.status).toBe(200);
    const uploadId = String((await started.json() as { upload_id: string }).upload_id);
    const parts: Array<{ etag: string; partNumber: number }> = [];
    const values = [new Uint8Array(5 * 1024 * 1024).fill(65), new Uint8Array([66, 67])];
    for (const [index, value] of values.entries()) {
      const response = await worker.fetch(new Request(
        `${origin}/__m22-multipart/part/${path}?uploadId=${encodeURIComponent(uploadId)}&partNumber=${index + 1}`,
        {
          method: "PUT",
          headers: { ...headers, "Content-Length": String(value.byteLength) },
          body: value,
        },
      ), uploadEnv);
      expect(response.status).toBe(200);
      parts.push(await response.json() as { etag: string; partNumber: number });
    }
    const receipt = JSON.stringify({ parts });
    const completed = await worker.fetch(new Request(
      `${origin}/__m22-multipart/complete/${path}?uploadId=${encodeURIComponent(uploadId)}`,
      {
        method: "POST",
        headers: { ...headers, "Content-Length": String(receipt.length) },
        body: receipt,
      },
    ), uploadEnv);
    expect(completed.status).toBe(201);
    const stored = await env.DATA.get(`${prefix}/${path}`);
    expect(stored?.size).toBe(5 * 1024 * 1024 + 2);
    expect(new Uint8Array(await stored!.arrayBuffer()).slice(-2)).toEqual(new Uint8Array([66, 67]));
  });
});
