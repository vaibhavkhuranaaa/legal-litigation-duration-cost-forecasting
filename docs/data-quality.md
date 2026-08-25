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

## Planned publication checks

The current evidence above covers the aggregate release. M16 through M22 must separately verify the
row-level serving mart before publication:

- exact reconciliation to 5,008,334 statistical records for the declared snapshot;
- zero prohibited fields and zero direct or natural identifiers;
- unique, non-reversible release record keys under the frozen M15 policy;
- all 362,615 collision records retained and labeled;
- exact reconciliation to every shared aggregate measure and supported grouping;
- complete partition manifest, compatible schema, declared null policy, and deterministic replay;
- exact pending, censoring, mapping, and source-record-count semantics; and
- export and full-download metadata that identify the same immutable dataset version.

No result is claimed for these checks until the corresponding milestone evidence is recorded.
