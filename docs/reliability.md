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
