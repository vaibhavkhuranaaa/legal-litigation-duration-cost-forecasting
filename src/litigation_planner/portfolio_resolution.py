"""Leakage-safe development evaluation for aggregate 12-month resolution forecasts."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb
import numpy as np

SAFE_RELATION = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


@dataclass(frozen=True)
class Fold:
    fold_id: str
    assessment_start: date
    assessment_end: date


@dataclass(frozen=True)
class PortfolioGates:
    overall_calibration_upper: float
    monthly_calibration_error: float
    estimate_coverage: float
    minimum_monthly_cases: int
    minimum_development_folds: int


@dataclass(frozen=True)
class PortfolioResolutionConfig:
    version: int
    capability_id: str
    prediction_unit: str
    target: str
    source_relation: str
    snapshot_cutoff: date
    horizon_days: int
    training_lookback_years: int
    bootstrap_replicates: int
    random_seed: int
    final_holdout_start: date
    final_holdout_end: date
    final_holdout_read: bool
    expected_digest: str
    gates: PortfolioGates
    folds: tuple[Fold, ...]

    @classmethod
    def from_toml(cls, path: Path) -> PortfolioResolutionConfig:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
        for field in ("snapshot_cutoff", "final_holdout_start", "final_holdout_end"):
            raw[field] = date.fromisoformat(raw[field])
        raw["gates"] = PortfolioGates(**raw["gates"])
        raw["folds"] = tuple(
            Fold(
                fold_id=fold["fold_id"],
                assessment_start=date.fromisoformat(fold["assessment_start"]),
                assessment_end=date.fromisoformat(fold["assessment_end"]),
            )
            for fold in raw["folds"]
        )
        config = cls(**raw)
        config.validate()
        return config

    def validate(self) -> None:
        if not SAFE_RELATION.fullmatch(self.source_relation):
            raise ValueError("source relation must be a qualified SQL identifier")
        if self.horizon_days <= 0 or self.training_lookback_years <= 0:
            raise ValueError("horizon and training lookback must be positive")
        if self.final_holdout_read:
            raise ValueError("development protocol cannot mark the final holdout as read")
        if self.final_holdout_start > self.final_holdout_end:
            raise ValueError("final holdout boundaries are invalid")
        if len(self.folds) < self.gates.minimum_development_folds:
            raise ValueError("insufficient rolling development folds")
        previous_end: date | None = None
        for fold in self.folds:
            if fold.assessment_start > fold.assessment_end:
                raise ValueError(f"invalid assessment window for {fold.fold_id}")
            if previous_end is not None and fold.assessment_start <= previous_end:
                raise ValueError("development folds must be strictly non-overlapping")
            if fold.assessment_end >= self.final_holdout_start:
                raise ValueError("development fold overlaps the sealed final holdout")
            if fold.assessment_end + timedelta(days=self.horizon_days) > self.snapshot_cutoff:
                raise ValueError("development fold lacks complete outcome follow-up")
            previous_end = fold.assessment_end
        observed = protocol_digest(self)
        if observed != self.expected_digest:
            raise ValueError(
                f"portfolio protocol digest mismatch: expected {self.expected_digest}, got {observed}"
            )


def protocol_digest(config: PortfolioResolutionConfig) -> str:
    payload = asdict(config)
    payload.pop("expected_digest")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def mature_training_window(
    assessment_start: date,
    horizon_days: int,
    lookback_years: int,
) -> tuple[date, date]:
    as_of_date = assessment_start - timedelta(days=1)
    training_end = as_of_date - timedelta(days=horizon_days)
    training_start = date(
        training_end.year - lookback_years,
        training_end.month,
        training_end.day,
    ) + timedelta(days=1)
    return training_start, training_end


def _cluster_bootstrap_interval(
    prediction: float,
    counts: np.ndarray,
    events: np.ndarray,
    replicates: int,
    seed: int,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    errors = np.empty(replicates, dtype=np.float64)
    for replicate in range(replicates):
        sample = rng.integers(0, len(counts), size=len(counts))
        observed = float(events[sample].sum() / counts[sample].sum())
        errors[replicate] = abs(prediction - observed)
    return tuple(float(value) for value in np.quantile(errors, [0.025, 0.975]))


def _evaluate_fold(
    connection: duckdb.DuckDBPyConnection,
    config: PortfolioResolutionConfig,
    fold: Fold,
    fold_index: int,
) -> dict[str, Any]:
    training_start, training_end = mature_training_window(
        fold.assessment_start,
        config.horizon_days,
        config.training_lookback_years,
    )
    relation = config.source_relation
    training = connection.execute(
        f"""
        select count(*)::bigint as cases,
               sum(case when event_observed and duration_days <= ? then 1 else 0 end)::bigint
                   as resolved
        from {relation}
        where filed_date between ? and ?
        """,
        [config.horizon_days, training_start, training_end],
    ).fetchone()
    training_cases, training_resolved = int(training[0]), int(training[1])
    if training_cases == 0:
        raise ValueError(f"{fold.fold_id} has no label-mature training cases")
    prediction = training_resolved / training_cases
    clusters = connection.execute(
        f"""
        select date_trunc('month', filed_date)::date as filing_month,
               district_code, nature_family, origin_code,
               count(*)::bigint as cases,
               sum(case when event_observed and duration_days <= ? then 1 else 0 end)::bigint
                   as resolved
        from {relation}
        where filed_date between ? and ?
        group by all
        order by all
        """,
        [config.horizon_days, fold.assessment_start, fold.assessment_end],
    ).fetchall()
    if not clusters:
        raise ValueError(f"{fold.fold_id} has no assessment cases")
    counts = np.asarray([row[-2] for row in clusters], dtype=np.int64)
    events = np.asarray([row[-1] for row in clusters], dtype=np.int64)
    assessment_cases = int(counts.sum())
    observed = float(events.sum() / assessment_cases)
    overall_error = abs(prediction - observed)
    interval = _cluster_bootstrap_interval(
        prediction,
        counts,
        events,
        config.bootstrap_replicates,
        config.random_seed + fold_index,
    )
    monthly: dict[str, list[int]] = {}
    for row in clusters:
        month = row[0].isoformat()
        aggregate = monthly.setdefault(month, [0, 0])
        aggregate[0] += int(row[-2])
        aggregate[1] += int(row[-1])
    monthly_checks = [
        {
            "filing_month": month,
            "cases": values[0],
            "observed_probability": values[1] / values[0],
            "calibration_error": abs(prediction - values[1] / values[0]),
        }
        for month, values in sorted(monthly.items())
        if values[0] >= config.gates.minimum_monthly_cases
    ]
    monthly_maximum = max(
        (record["calibration_error"] for record in monthly_checks),
        default=float("inf"),
    )
    checks = {
        "overall_calibration_upper": interval[1] <= config.gates.overall_calibration_upper,
        "monthly_calibration_error": monthly_maximum <= config.gates.monthly_calibration_error,
        "estimate_coverage": 1.0 >= config.gates.estimate_coverage,
    }
    return {
        "fold_id": fold.fold_id,
        "assessment_start": fold.assessment_start.isoformat(),
        "assessment_end": fold.assessment_end.isoformat(),
        "as_of_date": (fold.assessment_start - timedelta(days=1)).isoformat(),
        "label_mature_training_start": training_start.isoformat(),
        "label_mature_training_end": training_end.isoformat(),
        "training_cases": training_cases,
        "assessment_cases": assessment_cases,
        "predicted_probability": prediction,
        "observed_probability": observed,
        "overall_calibration_error": overall_error,
        "cluster_bootstrap_95": list(interval),
        "maximum_monthly_calibration_error": monthly_maximum,
        "monthly_checks": monthly_checks,
        "estimate_coverage": 1.0,
        "checks": checks,
        "passes": all(checks.values()),
    }


def run_development_evaluation(
    warehouse: Path,
    config_path: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    config = PortfolioResolutionConfig.from_toml(config_path)
    connection = duckdb.connect(str(warehouse), read_only=True)
    snapshot = connection.execute(
        f"select max(as_of_date) from {config.source_relation}"
    ).fetchone()[0]
    if snapshot != config.snapshot_cutoff:
        raise ValueError(f"warehouse snapshot {snapshot} does not match {config.snapshot_cutoff}")
    folds = [
        _evaluate_fold(connection, config, fold, index) for index, fold in enumerate(config.folds)
    ]
    connection.close()
    development_passes = all(fold["passes"] for fold in folds)
    report = {
        "protocol_version": config.version,
        "protocol_digest": protocol_digest(config),
        "capability_id": config.capability_id,
        "prediction_unit": config.prediction_unit,
        "target": config.target,
        "evaluation_scope": "development_only",
        "final_holdout_read": False,
        "final_holdout": {
            "start": config.final_holdout_start.isoformat(),
            "end": config.final_holdout_end.isoformat(),
        },
        "gates": asdict(config.gates),
        "bootstrap_cluster": [
            "filing_month",
            "district_code",
            "nature_family",
            "origin_code",
        ],
        "folds": folds,
        "development_passes": development_passes,
        "capability_status": ("awaiting_final" if development_passes else "development_failed"),
        "limitations": [
            "The target is an aggregate filing-cohort rate, never an individual estimate.",
            "Current-snapshot records cannot reconstruct every historical administrative revision.",
            "A passing development result would still require one untouched final evaluation.",
        ],
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    return report
