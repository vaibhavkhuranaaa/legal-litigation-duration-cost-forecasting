# Publish the governed row analytics release

## Decision

Publish release v2.0 with GitHub Pages serving the report application and a read-only Cloudflare
Worker serving the immutable, identifier-minimized row-data inventory from R2. This decision
supersedes the publication holds in decisions 0032 and 0033.

## Why

All 33 frozen M22 checks pass. The 38-file, 185,759,334-byte production inventory reconciles to all
5,008,334 governed records, contains zero prohibited values, and passes exact remote hash, byte-range,
MIME, CORS, immutable-cache, browser, rollback, and zero-incremental-cost checks. The application keeps
the aggregate cube as its initial-render fast path and fail-closed fallback.

## Alternatives rejected

- Keeping the verified candidate inactive was rejected after explicit publication approval because it
  would withhold a release that satisfies every frozen gate.
- Committing generated Parquet to Git was rejected because generated data must remain outside tracked
  source and Git history.
- Serving unbounded record queries was rejected because the publication contract requires annual
  partition activation, projection, stable sorting, cancellation, and result ceilings.

## Not done

This release does not publish source identifiers, names, text, private review evidence, credentials,
warehouses, or model artifacts. It does not enable duration forecasts, represent synthetic scenarios
as observed costs, or claim capacity beyond the declared zero-cost usage profile.

## Changed

The Pages build now injects the production row-data origin. The production Worker exposes only
allowlisted read-only release paths, and the application validates the manifest, schema, media type,
range behavior, CORS origin, and redirect policy before registering a partition. The superseded
candidate endpoint and its old immutable prefix are removed after production verification.
