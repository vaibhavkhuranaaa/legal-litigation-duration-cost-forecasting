"""Run all frozen protocol-v3 folds without reading the sealed final holdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from litigation_planner.survival_v3 import run_development_evaluation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path("config/survival-v3.toml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_development_evaluation(args.warehouse, args.protocol, args.output)
    print(json.dumps(report["development_policy_passes"], indent=2))


if __name__ == "__main__":
    main()
