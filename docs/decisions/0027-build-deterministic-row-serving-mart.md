# Build the deterministic row serving mart

Status: implemented locally for M16. This decision authorizes no upload, deployment, push,
publication, public row-data activation, or later milestone work.

## Decision

Build `fjc-civil-2026-03-31.v1` as 17 annual Zstandard Parquet partitions using the frozen 19-field
`public-row-mart.v1` allowlist and the M17 policy of 65,536 rows per row group. Sort each partition by
district, nature-of-suit family, and dataset-scoped opaque release key. Keep all generated data,
manifests, summaries, and key material in the private sibling workspace.

Use a canonical JSON manifest with one entry per annual file. Each entry binds filing year, row count,
byte size, dataset and schema versions, and SHA-256 integrity metadata. Treat the manifest and
partitions as one immutable candidate. Refuse existing output paths and any output or key path inside
tracked Git.

Reconcile the candidate at two levels. First, scan every physical partition for schema, opaque-key,
collision, censoring, date, null, mapping, identity, version, source-cutoff, and prohibited-content
rules. Second, rebuild the approved aggregate cube from the Parquet candidate and compare every
published supported grouping through exact counts and integer sufficient statistics. Keep derived
floating-point display values as a diagnostic, not as the equality boundary.

## Evidence

Each isolated build contains 5,008,334 records across 17 annual partitions and 18 total candidate
files including the manifest. It contains 5,008,334 distinct valid release keys, 362,615
collision-labeled records, 457,327 pending records, and zero prohibited findings in every partition.

Candidate size is 104,725,737 bytes: 104,719,878 partition bytes plus a 5,859-byte manifest. This is
157,418,263 bytes below the 262,144,000-byte release ceiling. All 18 files in the second isolated build
are byte-identical to the first.

Exact reconciliation passes 1,097 portfolio slices, 7,211 filing slices, and 662 pending-age slices
with zero count or integer-measure difference. Recomputed derived floating-point displays differ by at
most `5.684341886080802e-14` because aggregate order changes IEEE-754 rounding. Their exact count and
summed-day inputs are identical.

## Why

Annual files preserve M17 pruning behavior and keep common browser work bounded. Reusing the tested
single-partition builder applies one physical contract to both representative and full builds. Exact
integer sufficient statistics avoid treating harmless floating-point evaluation order as population
drift while still failing closed on any changed count or summed duration.

Two full isolated builds establish deterministic file and manifest replay against the pinned warehouse,
contract, key, DuckDB version, sort, compression, and row-group policy. The candidate remains private
because M16 proves build fitness only; public origin, terms, runtime, and release gates remain later work.

## Alternatives rejected

- Store generated Parquet in Git. Rejected because data and integrity records belong in the private
  sibling workspace and would exceed the public source boundary.
- Infer Hive partition columns from paths. Rejected because it adds an undeclared twentieth physical
  field; scans explicitly disable Hive partition injection.
- Compare aggregate display floats bit-for-bit. Rejected because equivalent integer inputs can differ
  at machine epsilon when aggregation order changes.
- Deduplicate collision records. Rejected because the frozen grain is one statistical record and all
  source ambiguity must remain visible.
- Upload a candidate for live validation. Rejected because M16 authorizes local construction only.

## Changed

- Added a full-mart builder around the existing annual partition builder.
- Added canonical manifest generation, integrity verification, full physical reconciliation, approved
  cube replay, byte-ceiling enforcement, and complete candidate comparison.
- Disabled automatic Hive partition-column injection for physical schema scans.
- Added focused checks for complete manifest structure, replay mismatch, exact cube projection, and
  refusal of public-repository output.

## Limitations

- Determinism is proven for identical pinned local inputs and tools, not a later data or dependency
  version.
- The HMAC key remains private and dataset-scoped; uniqueness does not make records anonymous.
- The manifest reserves `metrics.v1`; M18 must implement and verify that registry before application
  integration.
- M21 must repeat security, accessibility, reliability, and public-artifact checks against the finished
  browser product.
- M22 must reverify source terms and live origin behavior after fresh owner approval.

## Not done

- No semantic registry, report workspace, record explorer, export flow, or release package was built.
- No dataset, manifest, summary, key, or private path was added to Git.
- No upload, deployment, provider mutation, push, publication, public visibility change, or paid action
  occurred.
