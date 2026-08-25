# 0002 Reproducible source acquisition

## Decision

Pin March 31, 2026 as latest common FJC and AO reporting cutoff. Acquire FJC cumulative civil population, current civil codebook, research guide, AO tables C through C-5, and district profiles. Revalidate retained June 30, 2026 CourtListener docket snapshot in place as enrichment only. Store raw objects and immutable manifests outside public repository.

## Why

Current FJC cumulative file includes terminated and pending cases through March 31, 2026. Same-period AO tables support later reconciliation without pretending newer AO data extends FJC coverage. Content-addressed artifacts protect against mutable source URLs. Full archive checks, required-column checks, and schema fingerprints block corrupt or incompatible inputs.

## Alternatives rejected

- Use June 30, 2026 AO tables as product cutoff. FJC population has not advanced to that date.
- Download CourtListener again. Existing private snapshot passes full integrity, content, and schema checks.
- Store data or manifests in public repository. Public boundary forbids datasets and private provenance state.
- Use CourtListener as population. Its coverage is uneven and has no completeness guarantee.
- Upload to GCS during acquisition. Cloud mutation remains gated and belongs to raw-platform milestone.

## Not done

No FJC and RECAP join, data conversion, cloud upload, BigQuery query, canonical model, analytics result, model training, deployment, spend, push, or publication occurred.

## Changed

Added pinned source registry, bounded acquisition CLI, private-root enforcement, content-addressed artifact promotion, source-set manifests, ZIP, BZ2, XLSX, and PDF validation, schema fingerprints, retry tests, and source-acquisition documentation.
