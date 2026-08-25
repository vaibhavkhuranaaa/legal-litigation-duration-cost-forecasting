"""Evaluate the M7 survival baseline and challenger on private mart data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from litigation_planner.survival import run_survival_evaluation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/survival.toml"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_survival_evaluation(args.warehouse, args.config, args.output_dir)
    print(json.dumps(report["shipping_policy"], indent=2))


if __name__ == "__main__":
    main()
