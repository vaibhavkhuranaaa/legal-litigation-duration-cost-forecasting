# Reliability contract

Readiness is split by capability. Operations analytics and synthetic scenarios are ready;
duration forecasting and milestone-event inference remain unavailable. Health confirms process
liveness only. Provenance pins source and development cutoffs and identifies the failed model
state.

Every release replays malformed input, oversized input, rate limiting, deterministic forecast
refusal, synthetic-scenario determinism, public-boundary inspection, secret scanning, unit and
contract tests, frontend compilation, and an offline container smoke test. Raw and reconciliation
pipelines fail closed on schema, archive, checksum, or review-binding violations.

Rollback is image-based: retain the prior image digest and SQLite seed digest, stop the candidate,
start the prior digest, and confirm `/v1/health`, `/v1/readiness`, `/v1/provenance`, and the refusal
probe. Data artifacts are immutable and are never rewritten during rollback.

## Planned browser reliability

M21 adds probes for query timeout and cancellation, worker restart with preserved filter state, memory
ceilings, malformed or incompatible manifests, missing partitions, invalid content types, redirect,
CORS and range failures, cache invalidation, offline aggregate fallback, and deterministic retry.
Tests must cover the declared desktop and mobile profiles and must show that an ordinary query does not
fetch every partition.

Row-level rollback is manifest-based. The last verified application, aggregate cube, semantic registry,
and data manifest are activated as one compatible set. New partitions remain unreachable until the
complete candidate manifest passes validation. The current aggregate release remains the safe fallback.
