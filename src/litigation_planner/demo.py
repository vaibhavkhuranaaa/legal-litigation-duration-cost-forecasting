"""Deterministic deidentified aggregate seed for the offline release."""

from __future__ import annotations

import sqlite3
from pathlib import Path

PORTFOLIO = ("2026-03-31", 5_008_334, 457_327, 4_645_719, 2_065_537)
RELEASE_SCHEMA_VERSION = "2"
COHORTS = {
    "ordinary_original": (2_503_909, 0.6679, 0.8456, 0.0165),
    "multidistrict_litigation": (767_685, 0.2320, 0.3748, 0.1578),
    "other_procedural_origin": (551_610, 0.6984, 0.9046, 0.0109),
    "social_security_review": (237_239, 0.4793, 0.9586, 0.0027),
}


def build_demo_database(path: Path) -> None:
    """Build a matter-free SQLite database from approved aggregate constants."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE release_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
            CREATE TABLE portfolio (
                source_snapshot TEXT PRIMARY KEY,
                statistical_records INTEGER NOT NULL,
                pending_records INTEGER NOT NULL,
                collision_free_cases INTEGER NOT NULL,
                promoted_recap_matches INTEGER NOT NULL
            ) WITHOUT ROWID;
            CREATE TABLE cohort_benchmark (
                cohort TEXT PRIMARY KEY,
                cases INTEGER NOT NULL,
                termination_365_day_share REAL NOT NULL,
                termination_730_day_share REAL NOT NULL,
                snapshot_censored_share REAL NOT NULL
            ) WITHOUT ROWID;
            """
        )
        connection.executemany(
            "INSERT INTO release_metadata VALUES (?, ?)",
            [
                ("deidentified", "true"),
                ("matter_level_rows", "0"),
                ("model_status", "failed_not_promoted"),
                ("observed_cost_rows", "0"),
                ("release_version", RELEASE_SCHEMA_VERSION),
            ],
        )
        connection.execute("INSERT INTO portfolio VALUES (?, ?, ?, ?, ?)", PORTFOLIO)
        connection.executemany(
            "INSERT INTO cohort_benchmark VALUES (?, ?, ?, ?, ?)",
            [(name, *values) for name, values in sorted(COHORTS.items())],
        )
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()


def read_portfolio(path: Path) -> tuple[str, int, int, int, int]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        row = connection.execute(
            "SELECT source_snapshot, statistical_records, pending_records, "
            "collision_free_cases, promoted_recap_matches FROM portfolio"
        ).fetchone()
    if row is None:
        raise RuntimeError("demo portfolio seed is empty")
    return row


def read_cohort(path: Path, cohort: str) -> tuple[int, float, float, float]:
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        row = connection.execute(
            "SELECT cases, termination_365_day_share, termination_730_day_share, "
            "snapshot_censored_share FROM cohort_benchmark WHERE cohort = ?",
            (cohort,),
        ).fetchone()
    if row is None:
        raise RuntimeError("demo cohort is absent")
    return row
