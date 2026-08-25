# Source acquisition

M2 pins source URLs and reporting cutoffs in `config/sources.toml`. Raw files and generated manifests remain under ignored `data/` storage. Public Git contains code and contracts only.

Acquisition enforces three attempts, byte caps, resumable partial files, atomic content-addressed promotion, cryptographic content digests, archive integrity, schema fingerprints, and required source columns. A failed download stays as a `.part` file and cannot enter downstream work. CLI refuses raw or manifest destinations inside public repository.

Pinned population cutoff is March 31, 2026, matching current FJC cumulative civil data. AO tables C, C-1, C-3, C-4, C-5, and district profiles use same reporting cutoff. CourtListener June 30, 2026 snapshot remains enrichment only and cannot become population truth.

```sh
uv run --frozen python scripts/acquire_sources.py \
  --data-root /private/path/raw \
  --manifest-dir /private/path/manifests \
  --existing courtlistener_recap_dockets=/private/path/dockets-2026-06-30.csv.bz2 \
  --provenance-manifest courtlistener_recap_dockets=/private/path/dockets-2026-06-30.manifest.json
```

No acquisition uploads to GCS, queries BigQuery, joins FJC to RECAP, or promotes a canonical record.
