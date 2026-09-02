const DATASET_ROOT = "row-data/fjc-civil-2026-03-31.v1";
const RELEASE_PREFIX_PATTERN = /^releases\/[A-Za-z0-9._-]{1,160}$/;
const ASSET_PATH_PATTERN = /^assets\/[A-Za-z0-9._-]{1,180}$/;
const PARTITION_PATH_PATTERN = /^row-data\/fjc-civil-2026-03-31\.v1\/filing_year=20(?:1[0-9]|2[0-6])\/part-00000\.parquet$/;
const DATA_METADATA = new Set([
  `${DATASET_ROOT}/manifest.json`,
  `${DATASET_ROOT}/metrics.v1.json`,
  `${DATASET_ROOT}/data-dictionary.json`,
]);
const POPULATION_ASSET = "assets/full-population.v1-Bywqab--.json";
const COHORTS: Record<string, [number, number, number, number]> = {
  ordinary_original: [2_503_909, 0.6679, 0.8456, 0.0165],
  multidistrict_litigation: [767_685, 0.232, 0.3748, 0.1578],
  other_procedural_origin: [551_610, 0.6984, 0.9046, 0.0109],
  social_security_review: [237_239, 0.4793, 0.9586, 0.0027],
};
const INDEX_QUERY_KEYS = new Set(["report", "district", "nature", "cohort", "rank", "drill"]);

function errorResponse(status: number, code: string): Response {
  return Response.json(
    { error: code },
    {
      status,
      headers: {
        "cache-control": "no-store",
        "content-type": "application/json; charset=utf-8",
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
      },
    },
  );
}

function apiResponse(value: unknown): Response {
  return Response.json(value, {
    headers: {
      "cache-control": "no-cache",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
      "x-frame-options": "DENY",
    },
  });
}

function round(value: number): number {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

async function handleApi(request: Request, env: Env, url: URL): Promise<Response | null> {
  if (!url.pathname.startsWith("/v1/")) return null;
  if (url.search || url.hash) return errorResponse(400, "exact_url_required");
  const staticResponses: Record<string, unknown> = {
    "/v1/readiness": {
      status: "ready",
      operations_analytics: "ready",
      duration_forecast: "unavailable",
      milestone_events: "unavailable",
      scenario_engine: "ready",
      reason: "M7 model gates failed; operations analytics and synthetic scenarios remain available.",
    },
    "/v1/portfolio": {
      source_snapshot: "2026-03-31",
      statistical_records: 5_008_334,
      pending_records: 457_327,
      pending_share: 457_327 / 5_008_334,
      collision_free_cases: 4_645_719,
      promoted_recap_matches: 2_065_537,
      recap_match_coverage: 2_065_537 / 4_645_719,
      interpretation: "Observed nationwide public court metadata; not a duration forecast.",
    },
    "/v1/milestones/availability": {
      status: "event_unavailable",
      event_updates_enabled: false,
      match_coverage: 2_065_537 / 4_645_719,
      missing_event_fields: ["entry_number", "description"],
      fallback: "observed_portfolio_and_cohort_context",
      limitation: "No docket event is inferred from fields that are not present.",
    },
    "/v1/provenance": {
      release_version: "2",
      fjc_snapshot: "2026-03-31",
      recap_snapshot: "2026-06-30",
      development_outcomes_end: "2024-03-31",
      model_status: "failed_not_promoted",
      legal_advice: false,
      real_cost_forecast: false,
    },
  };
  if (url.pathname in staticResponses) {
    return request.method === "GET"
      ? apiResponse(staticResponses[url.pathname])
      : errorResponse(405, "method_not_allowed");
  }
  if (url.pathname === "/v1/population-explorer") {
    if (request.method !== "GET") return errorResponse(405, "method_not_allowed");
    if (!RELEASE_PREFIX_PATTERN.test(env.RELEASE_PREFIX)) {
      return errorResponse(503, "release_configuration_invalid");
    }
    const object = await env.DATA.get(`${env.RELEASE_PREFIX}/${POPULATION_ASSET}`);
    if (!object || !hasBody(object)) return errorResponse(404, "not_found");
    return new Response(object.body, {
      headers: {
        "cache-control": "no-cache",
        "content-type": "application/json; charset=utf-8",
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
      },
    });
  }
  if (url.pathname === "/v1/benchmarks") {
    if (request.method !== "POST") return errorResponse(405, "method_not_allowed");
    const body = await request.json() as { cohort?: unknown };
    const cohort = typeof body.cohort === "string" ? body.cohort : "";
    const values = COHORTS[cohort];
    if (!values) return errorResponse(400, "unknown_benchmark_cohort");
    return apiResponse({
      status: "observed_benchmark",
      cohort,
      cases: values[0],
      termination_365_day_share: values[1],
      termination_730_day_share: values[2],
      snapshot_censored_share: values[3],
      outcomes_through: "2024-03-31",
      limitation: "Historical cohort average; not a matter-specific prediction or legal advice.",
    });
  }
  if (url.pathname === "/v1/scenarios") {
    if (request.method !== "POST") return errorResponse(405, "method_not_allowed");
    const body = await request.json() as Record<string, unknown>;
    const keys = [
      "matters",
      "horizon_months",
      "attorney_hours_per_matter_month",
      "paralegal_hours_per_matter_month",
      "attorney_rate_usd",
      "paralegal_rate_usd",
    ];
    if (keys.some((key) => typeof body[key] !== "number" || !Number.isFinite(body[key]))) {
      return errorResponse(400, "invalid_scenario");
    }
    const values = Object.fromEntries(keys.map((key) => [key, Number(body[key])])) as Record<string, number>;
    const assumptions = {
      ...values,
      productive_hours_per_fte_month: 120,
      low_multiplier: 0.8,
      high_multiplier: 1.25,
    };
    const attorneyHours = values.matters * values.horizon_months * values.attorney_hours_per_matter_month;
    const paralegalHours = values.matters * values.horizon_months * values.paralegal_hours_per_matter_month;
    const baseCost = attorneyHours * values.attorney_rate_usd + paralegalHours * values.paralegal_rate_usd;
    const capacity = values.horizon_months * assumptions.productive_hours_per_fte_month;
    const createCase = (name: string, multiplier: number) => ({
      name,
      multiplier,
      attorney_hours: attorneyHours * multiplier,
      paralegal_hours: paralegalHours * multiplier,
      attorney_fte: round((attorneyHours * multiplier) / capacity),
      paralegal_fte: round((paralegalHours * multiplier) / capacity),
      budget_usd: round(baseCost * multiplier),
    });
    return apiResponse({
      scenario_type: "synthetic",
      observed_cost_data_used: false,
      assumptions,
      cases: [createCase("low", 0.8), createCase("base", 1), createCase("high", 1.25)],
      limitation: "User-supplied sensitivity scenario; not an observed bill or real cost forecast.",
    });
  }
  return errorResponse(404, "not_found");
}

function publicPath(pathname: string): string | null {
  if (pathname === "/") return "index.html";
  if (!pathname.startsWith("/") || pathname.includes("//")) return null;
  const path = pathname.slice(1);
  if (path === "index.html" || path === "release-manifest.json") return path;
  if (ASSET_PATH_PATTERN.test(path) || PARTITION_PATH_PATTERN.test(path) || DATA_METADATA.has(path)) {
    return path;
  }
  return null;
}

function validIndexQuery(url: URL): boolean {
  if (!url.search) return true;
  if (url.search.length > 512 || url.searchParams.size > INDEX_QUERY_KEYS.size) return false;
  const seen = new Set<string>();
  for (const [key, value] of url.searchParams) {
    if (
      !INDEX_QUERY_KEYS.has(key)
      || seen.has(key)
      || !/^[A-Za-z0-9_-]{1,64}$/.test(value)
    ) return false;
    seen.add(key);
  }
  return true;
}

function contentType(path: string): string {
  if (path.endsWith(".parquet")) return "application/vnd.apache.parquet";
  if (path.endsWith(".json")) return "application/json; charset=utf-8";
  if (path.endsWith(".html")) return "text/html; charset=utf-8";
  if (path.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (path.endsWith(".css")) return "text/css; charset=utf-8";
  if (path.endsWith(".wasm")) return "application/wasm";
  if (path.endsWith(".woff2")) return "font/woff2";
  if (path.endsWith(".woff")) return "font/woff";
  return "application/octet-stream";
}

function allowedOrigin(request: Request, env: Env): string | null {
  const origin = request.headers.get("origin");
  if (!origin) return null;
  return origin === env.CANDIDATE_ORIGIN || origin === env.PAGES_ORIGIN ? origin : "";
}

function applyCors(headers: Headers, origin: string | null): void {
  if (!origin) return;
  headers.set("access-control-allow-origin", origin);
  headers.set("access-control-expose-headers", "accept-ranges, cache-control, content-length, content-range, content-type, etag");
  headers.set("vary", "Origin");
}

function preflight(request: Request, env: Env, path: string): Response {
  const origin = allowedOrigin(request, env);
  if (!origin) return errorResponse(403, "origin_not_allowed");
  const method = request.headers.get("access-control-request-method")?.toUpperCase();
  const requestedHeaders = (request.headers.get("access-control-request-headers") ?? "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  if (!path || !["GET", "HEAD"].includes(method ?? "") || requestedHeaders.some((value) => value !== "range")) {
    return errorResponse(403, "preflight_not_allowed");
  }
  const headers = new Headers({
    "access-control-allow-headers": "Range",
    "access-control-allow-methods": "GET, HEAD, OPTIONS",
    "access-control-allow-origin": origin,
    "access-control-max-age": "86400",
    "cache-control": "no-store",
    vary: "Origin, Access-Control-Request-Headers, Access-Control-Request-Method",
  });
  return new Response(null, { status: 204, headers });
}

function validRangeHeader(value: string | null): boolean {
  if (!value) return true;
  const match = /^bytes=(\d*)-(\d*)$/.exec(value);
  return Boolean(match && (match[1] || match[2]));
}

function resolvedRange(range: R2Range, size: number): { offset: number; length: number } {
  if ("suffix" in range && typeof range.suffix === "number") {
    const length = Math.min(range.suffix, size);
    return { offset: size - length, length };
  }
  const offset = "offset" in range && typeof range.offset === "number" ? range.offset : 0;
  const declaredLength = "length" in range && typeof range.length === "number" ? range.length : size - offset;
  const length = Math.min(declaredLength, size - offset);
  return { offset, length };
}

function hasBody(object: R2Object): object is R2ObjectBody {
  return "body" in object && object.body instanceof ReadableStream;
}

function responseHeaders(path: string, object: R2Object, origin: string | null, ranged: boolean): Headers {
  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set("accept-ranges", "bytes");
  headers.set("content-type", contentType(path));
  headers.set("etag", object.httpEtag);
  headers.set("referrer-policy", "no-referrer");
  headers.set("x-content-type-options", "nosniff");
  headers.set("x-frame-options", "DENY");
  headers.set("permissions-policy", "camera=(), geolocation=(), microphone=(), payment=(), usb=()");
  headers.set("cache-control", path === "index.html" ? "no-cache" : "public, max-age=31536000, immutable");
  if (path.startsWith(`${DATASET_ROOT}/`)) {
    headers.set("cross-origin-resource-policy", "cross-origin");
  } else {
    headers.set("cross-origin-resource-policy", "same-origin");
  }
  if (path === "index.html") {
    headers.set("content-security-policy", "default-src 'none'; base-uri 'none'; connect-src 'self'; font-src 'self'; form-action 'none'; frame-ancestors 'none'; img-src 'self' data:; object-src 'none'; script-src 'self'; style-src 'self'; worker-src 'self' blob:");
    headers.set("cross-origin-opener-policy", "same-origin");
  }
  if (path.startsWith("assets/duckdb-browser-") && path.endsWith(".js")) {
    headers.set("cross-origin-embedder-policy", "require-corp");
  }
  if (ranged && object.range) {
    const range = resolvedRange(object.range, object.size);
    headers.set("content-length", String(range.length));
    headers.set("content-range", `bytes ${range.offset}-${range.offset + range.length - 1}/${object.size}`);
  } else {
    headers.set("content-length", String(object.size));
  }
  applyCors(headers, origin);
  return headers;
}

async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const api = await handleApi(request, env, url);
  if (api) return api;
  const path = publicPath(url.pathname);
  if (!path) return errorResponse(404, "not_found");
  if (url.hash || (url.search && (path !== "index.html" || !validIndexQuery(url)))) {
    return errorResponse(400, "exact_url_required");
  }
  if (request.method === "OPTIONS") return preflight(request, env, path);
  if (request.method !== "GET" && request.method !== "HEAD") {
    const response = errorResponse(405, "method_not_allowed");
    response.headers.set("allow", "GET, HEAD, OPTIONS");
    return response;
  }
  const origin = allowedOrigin(request, env);
  if (origin === "") return errorResponse(403, "origin_not_allowed");
  const rangeHeader = request.headers.get("range");
  if (!validRangeHeader(rangeHeader)) return errorResponse(416, "range_not_satisfiable");
  if (!RELEASE_PREFIX_PATTERN.test(env.RELEASE_PREFIX)) {
    return errorResponse(503, "release_configuration_invalid");
  }
  const key = `${env.RELEASE_PREFIX}/${path}`;
  const object = rangeHeader
    ? await env.DATA.get(key, { range: request.headers })
    : request.method === "HEAD"
      ? await env.DATA.head(key)
      : await env.DATA.get(key);
  if (!object) return errorResponse(404, "not_found");
  if (rangeHeader && !object.range) return errorResponse(416, "range_not_satisfiable");
  const headers = responseHeaders(path, object, origin, Boolean(rangeHeader));
  const status = rangeHeader ? 206 : 200;
  if (request.method === "HEAD") return new Response(null, { status, headers });
  if (!hasBody(object)) return errorResponse(412, "precondition_failed");
  return new Response(object.body, { status, headers });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      return await handleRequest(request, env);
    } catch (error) {
      console.error(JSON.stringify({
        error: error instanceof Error ? error.message : "unknown_error",
        event: "row_gateway_request_failed",
        path: new URL(request.url).pathname,
      }));
      return errorResponse(500, "internal_error");
    }
  },
} satisfies ExportedHandler<Env>;
