"""Create deterministic M9 evidence without observed cost data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from litigation_planner.scenarios import ScenarioAssumptions, build_scenario


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assumptions = ScenarioAssumptions(
        matters=25,
        horizon_months=12,
        attorney_hours_per_matter_month=4,
        paralegal_hours_per_matter_month=6,
        attorney_rate_usd=350,
        paralegal_rate_usd=150,
    )
    first = build_scenario(assumptions)
    second = build_scenario(assumptions)
    report = {
        "deterministic_replay": first == second,
        "synthetic_label_present": first["scenario_type"] == "synthetic",
        "observed_cost_data_used": first["observed_cost_data_used"],
        "example": first,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
