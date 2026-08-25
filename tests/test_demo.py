import sqlite3
from pathlib import Path

from litigation_planner.demo import build_demo_database, read_cohort, read_portfolio


def test_demo_seed_is_aggregate_only_and_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.sqlite"
    second = tmp_path / "second.sqlite"
    build_demo_database(first)
    build_demo_database(second)
    assert first.read_bytes() == second.read_bytes()
    assert read_portfolio(first)[1] == 5_008_334
    assert read_cohort(first, "social_security_review")[0] == 237_239
    with sqlite3.connect(first) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert tables == {"release_metadata", "portfolio", "cohort_benchmark"}
        assert connection.execute(
            "SELECT value FROM release_metadata WHERE key='matter_level_rows'"
        ).fetchone() == ("0",)
