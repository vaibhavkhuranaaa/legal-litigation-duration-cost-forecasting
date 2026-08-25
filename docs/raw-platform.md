# Raw platform

M3 converts the validated FJC cumulative civil source into private Zstandard Parquet with bounded Polars batches. A byte-level boundary first selects 40 approved metadata fields and excludes party and judge fields. Selected values must then decode as UTF-8 before Polars reads them. This handles invalid bytes observed only in excluded fields without silently changing source text.

The raw contract preserves source values as strings, including filing, termination, and AO-use dates. It adds source row number, parsed filing date, filing-year partition, snapshot cutoff, source digest, and raw contract version. It does not calculate duration, change nature-of-suit codes, or convert pending-case sentinels. Those semantics belong to the canonical warehouse milestone.

Rows filed before 2010 are counted as outside the product window. Rows with structural errors, invalid filing dates, dates after the source cutoff, or inconsistent status sentinels enter private quarantine with stable reason codes. Quarantine retains row references and digests, not party names or raw source lines. Accepted, excluded, and quarantined counts must reconcile to all source rows.

Outputs use filing-year partitions beneath a content-addressed source snapshot and contract-version directory. A completed run is immutable and a repeat request returns the existing success record. Source-level failures create a private failure record and leave no accepted output.

The GCS and BigQuery settings are deterministic plans only. GCS uses create-only object preconditions. BigQuery uses a deterministic job ID, snapshot-date partitioning, and district, filing-year, and nature-of-suit clustering. M3 does not upload, load, query, create, or alter cloud resources.

```sh
uv run --frozen python scripts/build_raw_platform.py \
  --manifest /private/ops/sources/manifests/fjc-civil.json \
  --source-root /private/ops/sources/raw \
  --output-root /private/ops/platform
```
