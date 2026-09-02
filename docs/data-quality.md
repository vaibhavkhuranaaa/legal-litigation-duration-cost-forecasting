# Data quality and fitness

The March 31, 2026 FJC cumulative snapshot contains 5,008,334 eligible statistical records from
2010 onward. It preserves 457,327 snapshot-pending records as right-censored. A collision-free
natural identifier supports 4,645,719 records; 362,615 records remain isolated as identity
exceptions. Exact codebook mapping supports 5,007,787 records, with 547 legacy-code records marked
unsupported rather than guessed.

The governed RECAP identity rule promotes 2,065,537 one-to-one matches with zero unresolved promoted
collisions. Blinded review of 800 candidates measured 100% precision with a 99.53995% exact
two-sided lower confidence bound. Coverage is 44.4611% of collision-free cases and does not imply
event-entry availability. Required entry number, filing date, and description fields are absent,
so milestone events are disabled.

AO national filing, termination, and pending comparisons pass the predeclared 0.5% tolerance. One
Southern District of Texas termination diagnostic remains outside the district threshold. Historical
duration summaries exclude censored cases and are descriptive only. The shipped SQLite seed has
only aggregate rows and contains no matter identifiers.

## Row-mart publication checks

M16 verifies the local row-level serving mart, M18 freezes the semantic layer, and M19 through M20
verify the synchronized interface and bounded record explorer. M21 completes the local reliability
gates. M22 repeats the candidate checks below and verifies them at the production public origin:

- exact reconciliation to 5,008,334 statistical records for the declared snapshot;
- zero prohibited fields and zero direct or natural identifiers;
- unique, non-reversible release record keys under the frozen M15 policy;
- all 362,615 collision records retained and labeled;
- exact reconciliation to every shared aggregate measure and supported grouping;
- complete partition manifest, compatible schema, declared null policy, and deterministic replay;
- exact pending, censoring, mapping, and source-record-count semantics; and
- export and full-download metadata that identify the same immutable dataset version.

M16 records exact population, collision, pending, aggregate, manifest, size, and replay results. M20
reconciles the frozen browser result and bounded exports, including deterministic provenance metadata.
M22 verifies an exact 38-file, 185,759,334-byte inventory against the privately retained digest. Every
live object matches the manifest, and range, MIME, CORS, cache, redirect, browser, cost, and
provider-rollback gates pass. The generated inventory remains outside Git and is active through the
read-only production Worker.
