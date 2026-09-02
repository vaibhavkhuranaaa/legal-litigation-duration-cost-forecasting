# Canonical dbt warehouse

## Governed grain

The FJC source is modeled first as statistical records. The documented circuit, district, office, and docket identifier is retained, but current-source collisions prevent a universal one-row-per-case claim.

| Model | Grain | Current rows | Consumer rule |
| --- | --- | ---: | --- |
| `fct_federal_civil_statistical_records` | One accepted FJC statistical record | 5,008,334 | Complete governed source population |
| `fct_federal_civil_cases` | One collision-free natural identifier | 4,645,719 | Eligible for later case-level reconciliation |
| `fct_fjc_identity_exceptions` | One record belonging to a colliding identifier | 362,615 | Blocked from case-level consumers |
| `dim_nature_of_suit` | One code supported by the retained codebook | 93 | Exact mapping only |

The exception mart contains 173,524 distinct colliding identifiers. No ranking, latest-row rule, or content hash is used to select a winner.

## Survival semantics

Status `L` is an observed termination. Status `S` is pending at the source cutoff. Pending records retain a null termination date, use the source cutoff as censoring date, and contribute censored duration. Actual source dates define duration. AO-use dates remain separate for M5 aggregate reconciliation.

## Nature-of-suit semantics

The retained official codebook supports 93 of 107 observed codes. Exact mappings cover 5,007,787 records. The remaining 547 records use 14 legacy codes not defined by that codebook. They retain the raw value and an `unsupported` status. M4 does not infer their labels, families, or effective periods.

## Local verification

Copy `analytics/profiles.yml.example` to the ignored `analytics/profiles.yml`, then point `FJC_RAW_PARQUET_GLOB` and `FJC_RAW_SUCCESS_JSON` at private M3 outputs.

```sh
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt --no-version-check debug --project-dir analytics --profiles-dir analytics --target local
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt --no-version-check source freshness --project-dir analytics --profiles-dir analytics --target local
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt --no-version-check build --project-dir analytics --profiles-dir analytics --target local --full-refresh
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt --no-version-check build --project-dir analytics --profiles-dir analytics --target local
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt --no-version-check docs generate --project-dir analytics --profiles-dir analytics --target local
```

The source freshness clock comes from the successful ingestion run record, not the historical source cutoff. The expected-failure fixture is disabled by default and CI selects it separately to prove an enforced type contract rejects incompatible output.

## Limits

- DuckDB is a private development adapter, not the scaled production platform.
- BigQuery syntax parsing is local evidence only. No query or build has run in BigQuery.
- The current build measures transformation correctness, not FJC and RECAP matching or model quality.
- The planned dbt exposure is low maturity and does not imply a live consumer.

The planned DuckDB-WASM report engine is not this private adapter and cannot open the development
warehouse. It queries only the M15-approved, denormalized Parquet serving mart. BigQuery remains an
approval-gated scaled alternative and is not a dependency of the planned public product.
