"""Authorize a development or final outcome read under the sealed M7 protocol."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import duckdb

from litigation_planner.survival import (
    ProtocolAuthorizationError,
    SealedSurvivalProtocol,
)


def _source_cutoff(warehouse: Path, relation: str) -> date:
    with duckdb.connect(str(warehouse), read_only=True) as connection:
        value = connection.execute(f"select max(as_of_date) from {relation}").fetchone()[0]
    if value is None:
        raise ValueError(f"source relation {relation} has no snapshot cutoff")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path("config/survival-v3.toml"))
    parser.add_argument("--mode", choices=("development", "final"), required=True)
    parser.add_argument("--outcomes-end", type=date.fromisoformat)
    parser.add_argument("--completed-attempts", type=int, default=0)
    args = parser.parse_args()

    protocol = SealedSurvivalProtocol.from_toml(args.protocol)
    cutoff = _source_cutoff(args.warehouse, protocol.source_relation)
    try:
        if args.mode == "development":
            outcomes_end = args.outcomes_end or protocol.development_outcomes_end
            protocol.authorize_development(outcomes_end)
        else:
            outcomes_end = protocol.final_holdout_end
            protocol.authorize_final(cutoff, args.completed_attempts)
    except ProtocolAuthorizationError as error:
        print(
            json.dumps(
                {
                    "authorized": False,
                    "mode": args.mode,
                    "source_cutoff": cutoff.isoformat(),
                    "reason": str(error),
                },
                indent=2,
            )
        )
        return 2

    print(
        json.dumps(
            {
                "authorized": True,
                "mode": args.mode,
                "outcomes_end": outcomes_end.isoformat(),
                "source_cutoff": cutoff.isoformat(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
