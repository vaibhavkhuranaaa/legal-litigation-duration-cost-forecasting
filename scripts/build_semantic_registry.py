from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from litigation_planner.semantic_registry import (
    SemanticRegistryError,
    evaluate_semantic_registry,
    load_semantic_registry,
    render_compiled_registry,
    render_metric_definitions,
)

if __package__:
    from scripts.build_public_row_mart import _scan_literal
    from scripts.build_representative_partition import _inside
else:
    from build_public_row_mart import _scan_literal
    from build_representative_partition import _inside


def build_registry(
    *,
    registry_path: Path,
    contract_path: Path,
    json_output: Path,
    markdown_output: Path,
    mart_root: Path | None = None,
    approved_cube_path: Path | None = None,
) -> dict[str, object] | None:
    registry = load_semantic_registry(registry_path, contract_path)
    json_output.write_text(render_compiled_registry(registry), encoding="utf-8")
    markdown_output.write_text(render_metric_definitions(registry), encoding="utf-8")
    if mart_root is None and approved_cube_path is None:
        return None
    if mart_root is None or approved_cube_path is None:
        raise SemanticRegistryError("mart root and approved cube must be supplied together")
    repository = Path(__file__).resolve().parents[1]
    if _inside(mart_root, repository):
        raise SemanticRegistryError("semantic evaluation mart must remain outside tracked Git")
    cube = json.loads(approved_cube_path.read_text(encoding="utf-8"))
    connection = duckdb.connect()
    try:
        scan = _scan_literal(mart_root)
        connection.execute(
            f"create view row_mart as select * from read_parquet({scan}, hive_partitioning = false)"
        )
        evaluation = evaluate_semantic_registry(connection, registry, cube)
        return {
            "status": "passed",
            "milestone": "M18",
            "candidate_state": "local_not_approved_for_publication",
            "registry_id": registry.registry_id,
            "dataset_version": registry.dataset_version,
            "schema_version": registry.schema_version,
            **evaluation,
            "incremental_cost_usd": 0.0,
        }
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compile and optionally reconcile the versioned semantic metric registry."
    )
    parser.add_argument("--registry", type=Path, default=Path("config/semantic-metrics-v1.toml"))
    parser.add_argument("--contract", type=Path, default=Path("config/public-row-mart-v1.toml"))
    parser.add_argument(
        "--json-output", type=Path, default=Path("frontend/src/semantic-metrics.v1.json")
    )
    parser.add_argument("--markdown-output", type=Path, default=Path("docs/semantic-metrics.md"))
    parser.add_argument("--mart-root", type=Path)
    parser.add_argument("--approved-cube", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = build_registry(
        registry_path=args.registry,
        contract_path=args.contract,
        json_output=args.json_output,
        markdown_output=args.markdown_output,
        mart_root=args.mart_root,
        approved_cube_path=args.approved_cube,
    )
    if result is None:
        print(f"{args.json_output}\n{args.markdown_output}")
        return
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.summary:
        if _inside(args.summary, Path(__file__).resolve().parents[1]):
            raise SemanticRegistryError(
                "semantic evaluation summary must remain outside tracked Git"
            )
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
