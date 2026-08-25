# 0018: Ship an aggregate offline demonstration

Status: accepted

## Decision

Package the built interface, typed API, and a deterministic deidentified aggregate SQLite seed in
a non-root container. Exclude warehouse, raw data, case-level data, credentials, cloud clients,
analytics toolchains, and model artifacts.

## Why

Reviewers need a complete product path that is reproducible without private data, cloud access, or
unsupported predictive claims.

## Alternatives rejected

Connecting the demo to DuckDB or BigQuery would expose private operational dependencies. Synthetic
case rows could be confused with evidence and are unnecessary for aggregate workflows.

## Not done

The image is not deployed, published, signed in a registry, or represented as internet-ready.

## Changed

Added deterministic aggregate seed construction, read-only SQLite access, compiled static serving,
multi-stage minimal packaging, a non-root user, offline replay, and container documentation.

## Consequences

The product can be reviewed locally without live BigQuery or source access. It demonstrates the
approved operations and synthetic-scenario workflows, not production deployment or prediction.
