"""Measure whether retained RECAP evidence can support milestone enrichment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from litigation_planner.milestones import assess_milestone_availability


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--matches", type=Path, required=True)
    parser.add_argument("--eligible-cases", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    columns = set(manifest["validation"]["schema"]["summary"]["columns"])
    matched_cases = pl.scan_parquet(args.matches).select(pl.len()).collect().item()
    result = assess_milestone_availability(columns, matched_cases, args.eligible_cases).to_dict()
    result.update(
        {
            "source_id": manifest["source_id"],
            "snapshot_cutoff": manifest["snapshot_cutoff"],
            "event_golden_set_cases": 0,
            "event_precision": None,
            "event_recall": None,
            "decision": "disable milestone enrichment; preserve observed-data fallback",
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
