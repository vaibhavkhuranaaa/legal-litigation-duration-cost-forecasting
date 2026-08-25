"""Run the sealed M7 v4 development protocol without reading final outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from litigation_planner.portfolio_resolution import run_development_evaluation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/portfolio-resolution.toml"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_development_evaluation(args.warehouse, args.config, args.output)
    print(
        json.dumps(
            {
                "capability_status": report["capability_status"],
                "development_passes": report["development_passes"],
                "final_holdout_read": report["final_holdout_read"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
