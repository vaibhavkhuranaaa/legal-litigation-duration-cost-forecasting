# Contributing

Contributions should preserve the product's evidence and data boundaries.

## Development checks

```sh
uv sync --frozen --extra dev
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
uv run python scripts/check_public_boundary.py
uv run python scripts/check_secrets.py
npm --prefix frontend ci
npm --prefix frontend run build
```

Use conventional commit subjects and keep each change focused. Update tests and documentation when a public contract changes.

## Data and model policy

Do not commit source datasets, warehouses, case-level exports, credentials, model binaries, generated build outputs, or private evaluation artifacts. Synthetic examples must be labeled. Failed model gates remain failed evidence and cannot be weakened after outcomes are reviewed.
