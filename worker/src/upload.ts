const DATASET_ROOT = "row-data/fjc-civil-2026-03-31.v1";
const RELEASE_PREFIX_PATTERN = /^releases\/m22-[a-f0-9]{64}$/;
const ASSET_PATH_PATTERN = /^assets\/[A-Za-z0-9._-]{1,180}$/;
const PARTITION_PATH_PATTERN = /^row-data\/fjc-civil-2026-03-31\.v1\/filing_year=20(?:1[0-9]|2[0-6])\/part-00000\.parquet$/;
const DATA_METADATA = new Set([
  `${DATASET_ROOT}/manifest.json`,
  `${DATASET_ROOT}/metrics.v1.json`,
  `${DATASET_ROOT}/data-dictionary.json`,
]);
const MAX_OBJECT_BYTES = 64 * 1024 * 1024;
const MAX_PART_BYTES = 6 * 1024 * 1024;

interface UploadEnv {
  DATA: R2Bucket;
  RELEASE_PREFIX: string;
  UPLOAD_TOKEN?: string;
}

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

function candidatePath(pathname: string): string | null {
  const prefix = "/__m22-upload/";
  if (!pathname.startsWith(prefix) || pathname.includes("//")) return null;
  const path = pathname.slice(prefix.length);
  if (path === "index.html" || path === "release-manifest.json") return path;
  if (ASSET_PATH_PATTERN.test(path) || PARTITION_PATH_PATTERN.test(path) || DATA_METADATA.has(path)) {
    return path;
  }
  return null;
}

function multipartPath(pathname: string, action: "start" | "part" | "complete"): string | null {
  const prefix = `/__m22-multipart/${action}/`;
  if (!pathname.startsWith(prefix) || pathname.includes("//")) return null;
  const candidate = pathname.slice(prefix.length);
  if (candidate === "index.html" || candidate === "release-manifest.json") return candidate;
  if (
    ASSET_PATH_PATTERN.test(candidate)
    || PARTITION_PATH_PATTERN.test(candidate)
    || DATA_METADATA.has(candidate)
  ) return candidate;
  return null;
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

async function tokenMatches(provided: string, expected: string): Promise<boolean> {
  const encoder = new TextEncoder();
  const [providedDigest, expectedDigest] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(provided)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected)),
  ]);
  const providedBytes = new Uint8Array(providedDigest);
  const expectedBytes = new Uint8Array(expectedDigest);
  let difference = 0;
  for (let index = 0; index < providedBytes.length; index += 1) {
    difference |= providedBytes[index] ^ expectedBytes[index];
  }
  return difference === 0;
}

async function authorized(request: Request, env: UploadEnv): Promise<boolean> {
  if (!env.UPLOAD_TOKEN) return false;
  return tokenMatches(request.headers.get("authorization") ?? "", `Bearer ${env.UPLOAD_TOKEN}`);
}

function configured(env: UploadEnv): boolean {
  return RELEASE_PREFIX_PATTERN.test(env.RELEASE_PREFIX) && Boolean(env.UPLOAD_TOKEN);
}

function objectKey(env: UploadEnv, path: string): string {
  return `${env.RELEASE_PREFIX}/${path}`;
}

function objectMetadata(path: string): R2PutOptions {
  return {
    httpMetadata: {
      cacheControl: path === "index.html" ? "no-cache" : "public, max-age=31536000, immutable",
      contentType: contentType(path),
    },
  };
}

async function handleMultipart(request: Request, env: UploadEnv, url: URL): Promise<Response | null> {
  const actions = ["start", "part", "complete"] as const;
  const action = actions.find((candidate) => multipartPath(url.pathname, candidate));
  if (!action) return null;
  const path = multipartPath(url.pathname, action);
  if (!path) return errorResponse(404, "not_found");
  if (!configured(env)) return errorResponse(503, "upload_configuration_invalid");
  if (!(await authorized(request, env))) return errorResponse(404, "not_found");
  const key = objectKey(env, path);
  if (action === "start") {
    if (request.method !== "POST" || url.search) return errorResponse(400, "invalid_multipart_start");
    const upload = await env.DATA.createMultipartUpload(key, objectMetadata(path));
    return Response.json({ upload_id: upload.uploadId }, { headers: { "cache-control": "no-store" } });
  }
  const uploadId = url.searchParams.get("uploadId") ?? "";
  if (url.searchParams.size !== (action === "part" ? 2 : 1) || !/^[A-Za-z0-9._~-]{8,512}$/.test(uploadId)) {
    return errorResponse(400, "invalid_multipart_identifier");
  }
  const upload = env.DATA.resumeMultipartUpload(key, uploadId);
  if (action === "part") {
    if (request.method !== "PUT" || !request.body) return errorResponse(400, "invalid_multipart_part");
    const partNumber = Number(url.searchParams.get("partNumber"));
    const declaredSize = Number(request.headers.get("content-length"));
    if (
      !Number.isSafeInteger(partNumber)
      || partNumber < 1
      || partNumber > 64
      || !Number.isSafeInteger(declaredSize)
      || declaredSize < 1
      || declaredSize > MAX_PART_BYTES
    ) return errorResponse(413, "invalid_multipart_part");
    const part = await upload.uploadPart(partNumber, request.body);
    return Response.json(part, { headers: { "cache-control": "no-store" } });
  }
  if (request.method !== "POST") return errorResponse(400, "invalid_multipart_complete");
  const declaredSize = Number(request.headers.get("content-length"));
  if (!Number.isSafeInteger(declaredSize) || declaredSize < 2 || declaredSize > 64 * 1024) {
    return errorResponse(413, "invalid_multipart_receipt");
  }
  const payload = await request.json() as { parts?: Array<{ etag?: unknown; partNumber?: unknown }> };
  if (!Array.isArray(payload.parts) || payload.parts.length < 2 || payload.parts.length > 64) {
    return errorResponse(400, "invalid_multipart_receipt");
  }
  const parts: R2UploadedPart[] = [];
  for (const [index, part] of payload.parts.entries()) {
    if (
      part.partNumber !== index + 1
      || typeof part.etag !== "string"
      || !/^[A-Za-z0-9._~+\/=:-]{8,512}$/.test(part.etag)
    ) return errorResponse(400, "invalid_multipart_receipt");
    parts.push({ etag: part.etag, partNumber: part.partNumber });
  }
  const object = await upload.complete(parts);
  return Response.json(
    { byte_size: object.size, path, status: "stored" },
    { status: 201, headers: { "cache-control": "no-store" } },
  );
}

async function handleUpload(request: Request, env: UploadEnv): Promise<Response> {
  const url = new URL(request.url);
  const multipartResponse = await handleMultipart(request, env, url);
  if (multipartResponse) return multipartResponse;
  if (url.search || url.hash) return errorResponse(400, "exact_url_required");
  if (request.method !== "PUT") return errorResponse(404, "not_found");
  const path = candidatePath(url.pathname);
  if (!path) return errorResponse(404, "not_found");
  if (!configured(env)) {
    return errorResponse(503, "upload_configuration_invalid");
  }
  if (!(await authorized(request, env))) return errorResponse(404, "not_found");
  const declaredSize = Number(request.headers.get("content-length"));
  if (!Number.isSafeInteger(declaredSize) || declaredSize < 1 || declaredSize > MAX_OBJECT_BYTES) {
    return errorResponse(413, "invalid_object_size");
  }
  if (!request.body) return errorResponse(400, "body_required");
  await env.DATA.put(objectKey(env, path), request.body, objectMetadata(path));
  return Response.json(
    { byte_size: declaredSize, path, status: "stored" },
    { status: 201, headers: { "cache-control": "no-store" } },
  );
}

export default {
  async fetch(request: Request, env: UploadEnv): Promise<Response> {
    try {
      return await handleUpload(request, env);
    } catch (error) {
      console.error(JSON.stringify({
        error: error instanceof Error ? error.message : "unknown_error",
        event: "candidate_upload_failed",
      }));
      return errorResponse(500, "internal_error");
    }
  },
} satisfies ExportedHandler<UploadEnv>;
