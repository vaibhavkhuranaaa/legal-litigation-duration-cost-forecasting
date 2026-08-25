"""Build the release SQLite seed."""

from __future__ import annotations

import argparse
from pathlib import Path

from litigation_planner.demo import build_demo_database


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build_demo_database(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
