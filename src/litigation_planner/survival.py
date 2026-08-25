"""Time-ordered intake survival evaluation and champion selection."""

from __future__ import annotations

import json
import math
import tomllib
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import polars as pl
import xgboost as xgb
from scipy.optimize import minimize
from scipy.special import ndtr

from litigation_planner.gate_policy import (
    CapabilityContract,
    EvidenceScope,
    GatePolicy,
    Gates,
    assert_frozen_policy,
    assess_shipping_policy,
)
from litigation_planner.security import SecurityBoundaryError, require_outside_repository

FEATURE_COLUMNS = ("district_code", "nature_family", "jurisdiction_code", "origin_code")


@dataclass(frozen=True)
class ChallengerConfig:
    distribution: str
    aft_loss_distribution_scale: float
    max_depth: int
    learning_rate: float
    max_rounds: int
    early_stopping_rounds: int
    min_child_weight: int
    subsample: float
    colsample_bytree: float
    nthread: int


@dataclass(frozen=True)
class SurvivalConfig:
    version: int
    source_relation: str
    snapshot_cutoff: date
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date
    baseline_lookback_start: date
    minimum_training_cases: int
    minimum_slice_cases: int
    horizons_days: tuple[int, ...]
    brier_grid_days: tuple[int, ...]
    bootstrap_replicates: int
    random_seed: int
    gates: Gates
    policy: GatePolicy
    challenger: ChallengerConfig

    @classmethod
    def from_toml(cls, path: Path) -> SurvivalConfig:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
        for field in (
            "snapshot_cutoff",
            "train_start",
            "train_end",
            "validation_start",
            "validation_end",
            "test_start",
            "test_end",
            "baseline_lookback_start",
        ):
            raw[field] = date.fromisoformat(raw[field])
        raw["horizons_days"] = tuple(raw["horizons_days"])
        raw["brier_grid_days"] = tuple(raw["brier_grid_days"])
        raw["gates"] = Gates(**raw["gates"])
        policy = raw["policy"]
        capability = policy["capability"]
        raw["policy"] = GatePolicy(
            policy_id=policy["policy_id"],
            protocol_version=raw["version"],
            capability=CapabilityContract(
                capability_id=capability["capability_id"],
                unit_of_analysis=capability["unit_of_analysis"],
                target=capability["target"],
                population=capability["population"],
                horizons_days=tuple(capability["horizons_days"]),
            ),
            thresholds=raw["gates"],
            minimum_slice_cases=raw["minimum_slice_cases"],
            expected_digest=policy["expected_digest"],
        )
        raw["challenger"] = ChallengerConfig(**raw["challenger"])
        config = cls(**raw)
        config.validate()
        return config

    def validate(self) -> None:
        if not (
            self.train_start
            <= self.train_end
            < self.validation_start
            <= self.validation_end
            < self.test_start
            <= self.test_end
            <= self.snapshot_cutoff
        ):
            raise ValueError("survival split boundaries must be strictly non-overlapping")
        if not self.train_start <= self.baseline_lookback_start <= self.train_end:
            raise ValueError("baseline lookback must fall inside training")
        if tuple(sorted(set(self.brier_grid_days))) != self.brier_grid_days:
            raise ValueError("Brier grid must be strictly increasing and unique")
        if any(horizon not in self.brier_grid_days for horizon in self.horizons_days):
            raise ValueError("every declared horizon must appear in the Brier grid")
        if max(self.brier_grid_days) > min(
            (self.snapshot_cutoff - self.validation_end).days,
            (self.snapshot_cutoff - self.test_end).days,
        ):
            raise ValueError("evaluation horizon exceeds complete administrative follow-up")
        if self.policy.protocol_version != self.version:
            raise ValueError("gate policy protocol version does not match survival config")
        if self.policy.capability.horizons_days != self.horizons_days:
            raise ValueError("gate policy horizons do not match survival config")
        assert_frozen_policy(self.policy)


class ProtocolAuthorizationError(ValueError):
    """Raised before a sealed protocol could read an unauthorized outcome window."""


@dataclass(frozen=True)
class DevelopmentFold:
    name: str
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    assessment_start: date
    assessment_end: date


@dataclass(frozen=True)
class SealedSurvivalProtocol:
    version: int
    status: str
    source_relation: str
    required_snapshot_cutoff: date
    development_outcomes_end: date
    final_holdout_start: date
    final_holdout_end: date
    horizons_days: tuple[int, ...]
    final_score_attempts: int
    intake_features: tuple[str, ...]
    forbidden_features: tuple[str, ...]
    development_folds: tuple[DevelopmentFold, ...]

    @classmethod
    def from_toml(cls, path: Path) -> SealedSurvivalProtocol:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
        folds = tuple(
            DevelopmentFold(
                **{
                    key: date.fromisoformat(value) if key != "name" else value
                    for key, value in fold.items()
                }
            )
            for fold in raw["development_fold"]
        )
        protocol = cls(
            version=int(raw["version"]),
            status=str(raw["status"]),
            source_relation=str(raw["source_relation"]),
            required_snapshot_cutoff=date.fromisoformat(raw["required_snapshot_cutoff"]),
            development_outcomes_end=date.fromisoformat(raw["development_outcomes_end"]),
            final_holdout_start=date.fromisoformat(raw["final_holdout_start"]),
            final_holdout_end=date.fromisoformat(raw["final_holdout_end"]),
            horizons_days=tuple(int(value) for value in raw["horizons_days"]),
            final_score_attempts=int(raw["final_score_attempts"]),
            intake_features=tuple(raw["intake_features"]),
            forbidden_features=tuple(raw["forbidden_features"]),
            development_folds=folds,
        )
        protocol.validate()
        return protocol

    def validate(self) -> None:
        if self.version != 3 or self.status != "sealed_pending_source":
            raise ValueError("protocol must remain sealed as version 3 pending source")
        if not self.development_outcomes_end < self.final_holdout_start:
            raise ValueError("development outcomes must end before the final holdout")
        if self.final_holdout_start > self.final_holdout_end:
            raise ValueError("final holdout boundaries must be time ordered")
        if set(self.intake_features) & set(self.forbidden_features):
            raise ValueError("intake and forbidden feature sets must be disjoint")
        if self.final_score_attempts != 1:
            raise ValueError("sealed final holdout must permit exactly one score attempt")
        for fold in self.development_folds:
            if not (
                fold.train_start
                <= fold.train_end
                < fold.validation_start
                <= fold.validation_end
                < fold.assessment_start
                <= fold.assessment_end
                <= self.development_outcomes_end
            ):
                raise ValueError(f"development fold {fold.name} is not time ordered")

    def authorize_development(self, requested_outcomes_end: date) -> None:
        if requested_outcomes_end > self.development_outcomes_end:
            raise ProtocolAuthorizationError(
                "development outcome access refused: requested end "
                f"{requested_outcomes_end.isoformat()} exceeds frozen development end "
                f"{self.development_outcomes_end.isoformat()}"
            )

    def authorize_final(self, snapshot_cutoff: date, completed_attempts: int = 0) -> None:
        if completed_attempts >= self.final_score_attempts:
            raise ProtocolAuthorizationError(
                "final outcome access refused: the sealed score-attempt allowance is exhausted"
            )
        if snapshot_cutoff < self.required_snapshot_cutoff:
            raise ProtocolAuthorizationError(
                "final outcome access refused: source cutoff "
                f"{snapshot_cutoff.isoformat()} is earlier than required cutoff "
                f"{self.required_snapshot_cutoff.isoformat()}"
            )
        available_followup = (snapshot_cutoff - self.final_holdout_end).days
        required_followup = max(self.horizons_days)
        if available_followup < required_followup:
            raise ProtocolAuthorizationError(
                "final outcome access refused: source provides "
                f"{available_followup} days of holdout follow-up; "
                f"{required_followup} are required"
            )


def _json_default(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def kaplan_meier_from_counts(
    durations: np.ndarray,
    events: np.ndarray,
    counts: np.ndarray,
    times: np.ndarray,
) -> np.ndarray:
    """Evaluate a Kaplan-Meier curve from duration-level event/censor counts."""
    order = np.argsort(durations, kind="stable")
    durations = durations[order]
    events = events[order]
    counts = counts[order]
    at_risk = int(counts.sum())
    survival = 1.0
    curve_times: list[int] = []
    curve_values: list[float] = []
    for duration in np.unique(durations):
        mask = durations == duration
        deaths = int(counts[mask & events].sum())
        removed = int(counts[mask].sum())
        if deaths:
            survival *= 1.0 - deaths / at_risk
        curve_times.append(int(duration))
        curve_values.append(survival)
        at_risk -= removed
    positions = np.searchsorted(curve_times, times, side="right") - 1
    result = np.ones(len(times), dtype=np.float64)
    selected = positions >= 0
    result[selected] = np.asarray(curve_values)[positions[selected]]
    return result


def _km_curves(
    connection: duckdb.DuckDBPyConnection,
    relation: str,
    config: SurvivalConfig,
    times: np.ndarray,
) -> tuple[dict[tuple[str, ...], np.ndarray], dict[tuple[str, ...], int]]:
    where = (
        f"filed_date between DATE '{config.baseline_lookback_start}' "
        f"and DATE '{config.train_end}' and nature_family <> 'unsupported'"
    )
    levels = (
        (
            "exact",
            "district_code, nature_family, jurisdiction_code, origin_code",
            4,
        ),
        ("district_origin", "district_code, nature_family, origin_code", 3),
        ("district", "district_code, nature_family", 2),
        ("nature_origin", "nature_family, jurisdiction_code, origin_code", 3),
        ("nature", "nature_family", 1),
        ("global", "'all' as group_value", 1),
    )
    curves: dict[tuple[str, ...], np.ndarray] = {}
    supports: dict[tuple[str, ...], int] = {}
    for level, columns, key_width in levels:
        rows = connection.execute(
            f"""
            select {columns}, duration_days, event_observed, count(*) as records
            from {relation}
            where {where}
            group by all
            order by all
            """
        ).fetchall()
        grouped: dict[tuple[str, ...], list[tuple[int, bool, int]]] = {}
        for row in rows:
            values = tuple(str(value) for value in row[:key_width])
            key = (level, *values)
            grouped.setdefault(key, []).append((int(row[-3]), bool(row[-2]), int(row[-1])))
        for key, values in grouped.items():
            array = np.asarray(values, dtype=np.int64)
            supports[key] = int(array[:, 2].sum())
            curves[key] = kaplan_meier_from_counts(
                array[:, 0], array[:, 1].astype(bool), array[:, 2], times
            )
    return curves, supports


def _baseline_probabilities(
    frame: pl.DataFrame,
    curves: dict[tuple[str, ...], np.ndarray],
    supports: dict[tuple[str, ...], int],
    minimum_support: int,
    width: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    probabilities = np.full((frame.height, width), np.nan, dtype=np.float32)
    supported = np.zeros(frame.height, dtype=bool)
    routes = {
        "exact": 0,
        "district_nature_origin": 0,
        "district_nature": 0,
        "nature_jurisdiction_origin": 0,
        "nature": 0,
        "global": 0,
        "unsupported": 0,
    }
    districts = frame["district_code"].to_list()
    natures = frame["nature_family"].to_list()
    jurisdictions = frame["jurisdiction_code"].to_list()
    origins = frame["origin_code"].to_list()
    for index, (district, nature, jurisdiction, origin) in enumerate(
        zip(districts, natures, jurisdictions, origins, strict=True)
    ):
        if nature == "unsupported":
            routes["unsupported"] += 1
            continue
        candidates = (
            ("exact", str(district), str(nature), str(jurisdiction), str(origin)),
            ("district_origin", str(district), str(nature), str(origin)),
            ("district", str(district), str(nature)),
            ("nature_origin", str(nature), str(jurisdiction), str(origin)),
            ("nature", str(nature)),
            ("global", "all"),
        )
        routes_in_order = (
            "exact",
            "district_nature_origin",
            "district_nature",
            "nature_jurisdiction_origin",
            "nature",
            "global",
        )
        for route, key in zip(routes_in_order, candidates, strict=True):
            if supports.get(key, 0) >= minimum_support:
                probabilities[index] = 1.0 - curves[key]
                supported[index] = True
                routes[route] += 1
                break
    return probabilities, supported, routes


def _load_frame(
    connection: duckdb.DuckDBPyConnection,
    relation: str,
    start: date,
    end: date,
) -> pl.DataFrame:
    return connection.execute(
        f"""
        select source_record_identifier, district_code, nature_family,
               jurisdiction_code, origin_code, year(filed_date)::integer as filing_year,
               duration_days::integer as duration_days, event_observed
        from {relation}
        where filed_date between DATE '{start}' and DATE '{end}'
        order by source_record_identifier
        """
    ).pl()


def _complete_outcomes(frame: pl.DataFrame, times: np.ndarray) -> np.ndarray:
    durations = frame["duration_days"].to_numpy()
    events = frame["event_observed"].to_numpy()
    if np.any((~events) & (durations < int(times.max()))):
        raise ValueError("evaluation includes censoring before the declared horizon")
    return events[:, None] & (durations[:, None] <= times[None, :])


def _category_maps(frame: pl.DataFrame) -> dict[str, dict[str, int]]:
    return {
        column: {
            value: index for index, value in enumerate(frame[column].unique().sort().to_list())
        }
        for column in FEATURE_COLUMNS
    }


def _feature_matrix(frame: pl.DataFrame, maps: dict[str, dict[str, int]]) -> np.ndarray:
    columns = []
    for column in FEATURE_COLUMNS:
        columns.append(
            frame[column]
            .replace_strict(maps[column], default=None, return_dtype=pl.Int32)
            .cast(pl.Float32)
            .to_numpy()
        )
    columns.append(frame["filing_year"].cast(pl.Float32).to_numpy())
    return np.column_stack(columns).astype(np.float32, copy=False)


def _aft_matrix(features: np.ndarray, frame: pl.DataFrame | None = None) -> xgb.DMatrix:
    matrix = xgb.DMatrix(
        features,
        feature_names=[*FEATURE_COLUMNS, "filing_year"],
        feature_types=["c", "c", "c", "c", "q"],
    )
    if frame is None:
        return matrix
    durations = np.maximum(frame["duration_days"].to_numpy().astype(np.float32), 1.0)
    events = frame["event_observed"].to_numpy()
    matrix.set_float_info("label_lower_bound", durations)
    matrix.set_float_info("label_upper_bound", np.where(events, durations, np.inf))
    return matrix


def _aft_event_probabilities(
    locations: np.ndarray,
    times: np.ndarray,
    intercept: float,
    slope: float,
    scale: float,
) -> np.ndarray:
    adjusted = intercept + slope * locations[:, None]
    z = (np.log(times)[None, :] - adjusted) / scale
    return ndtr(z).astype(np.float32)


def _calibrate_aft(
    locations: np.ndarray,
    outcomes: np.ndarray,
    times: np.ndarray,
    initial_scale: float,
) -> tuple[float, float, float]:
    def objective(parameters: np.ndarray) -> float:
        probabilities = _aft_event_probabilities(
            locations, times, parameters[0], parameters[1], math.exp(parameters[2])
        )
        return float(np.mean(np.square(probabilities - outcomes)))

    result = minimize(
        objective,
        np.asarray([0.0, 1.0, math.log(initial_scale)]),
        method="L-BFGS-B",
        bounds=((-2.0, 2.0), (0.5, 1.5), (math.log(0.25), math.log(4.0))),
    )
    if not result.success:
        raise RuntimeError(f"AFT calibration failed: {result.message}")
    return float(result.x[0]), float(result.x[1]), float(math.exp(result.x[2]))


def _bootstrap_interval(
    values: np.ndarray,
    replicates: int,
    seed: int,
    statistic: str = "mean",
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    estimates = np.empty(replicates, dtype=np.float64)
    for index in range(replicates):
        sample = rng.integers(0, len(values), size=len(values))
        if statistic == "absolute_mean":
            estimates[index] = abs(float(values[sample].mean()))
        else:
            estimates[index] = float(values[sample].mean())
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def _bootstrap_ibs_improvement(
    baseline: np.ndarray,
    challenger: np.ndarray,
    replicates: int,
    seed: int,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    estimates = np.empty(replicates, dtype=np.float64)
    for index in range(replicates):
        sample = rng.integers(0, len(baseline), size=len(baseline))
        estimates[index] = 1.0 - float(challenger[sample].mean() / baseline[sample].mean())
    return tuple(float(value) for value in np.quantile(estimates, [0.025, 0.975]))


def _slice_calibration(
    frame: pl.DataFrame,
    probabilities: np.ndarray,
    outcomes: np.ndarray,
    supported: np.ndarray,
    horizons: tuple[int, ...],
    minimum_cases: int,
) -> tuple[float, list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    for dimension in FEATURE_COLUMNS:
        values = frame[dimension].to_numpy()
        for value in np.unique(values[supported]):
            mask = supported & (values == value)
            count = int(mask.sum())
            if count < minimum_cases:
                continue
            errors = np.abs(probabilities[mask].mean(axis=0) - outcomes[mask].mean(axis=0))
            records.append(
                {
                    "dimension": dimension,
                    "value": str(value),
                    "cases": count,
                    "errors": {
                        str(horizon): float(error)
                        for horizon, error in zip(horizons, errors, strict=True)
                    },
                    "maximum_error": float(errors.max()),
                }
            )
    maximum = max((record["maximum_error"] for record in records), default=1.0)
    records.sort(key=lambda record: record["maximum_error"], reverse=True)
    return float(maximum), records


def evaluate_estimator(
    name: str,
    frame: pl.DataFrame,
    probabilities: np.ndarray,
    supported: np.ndarray,
    config: SurvivalConfig,
) -> tuple[dict[str, Any], np.ndarray]:
    grid = np.asarray(config.brier_grid_days)
    horizons = np.asarray(config.horizons_days)
    outcomes_grid = _complete_outcomes(frame, grid)
    outcomes_horizons = _complete_outcomes(frame, horizons)
    horizon_positions = np.searchsorted(grid, horizons)
    horizon_probabilities = probabilities[:, horizon_positions]
    residuals = outcomes_horizons[supported] - horizon_probabilities[supported]
    calibration = np.abs(residuals.mean(axis=0))
    intervals = [
        _bootstrap_interval(
            residuals[:, index],
            config.bootstrap_replicates,
            config.random_seed + index,
            "absolute_mean",
        )
        for index in range(len(horizons))
    ]
    slice_maximum, slices = _slice_calibration(
        frame,
        horizon_probabilities,
        outcomes_horizons,
        supported,
        config.horizons_days,
        config.minimum_slice_cases,
    )
    squared = np.square(probabilities[supported] - outcomes_grid[supported])
    case_ibs = np.trapezoid(squared, grid, axis=1) / (grid[-1] - grid[0])
    metrics = {
        "name": name,
        "eligible_cases": frame.height,
        "estimated_cases": int(supported.sum()),
        "estimate_coverage": float(supported.mean()),
        "calibration": {
            str(horizon): {
                "error": float(error),
                "bootstrap_95": list(interval),
            }
            for horizon, error, interval in zip(horizons, calibration, intervals, strict=True)
        },
        "supported_slice_maximum_error": slice_maximum,
        "supported_slice_count": len(slices),
        "worst_supported_slices": slices[:20],
        "integrated_brier_score": float(case_ibs.mean()),
    }
    return metrics, case_ibs


def run_survival_evaluation(
    warehouse: Path,
    config_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    config = SurvivalConfig.from_toml(config_path)
    try:
        require_outside_repository(output_dir)
    except SecurityBoundaryError as error:
        raise ValueError(str(error)) from error
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(warehouse), read_only=True)
    relation = config.source_relation
    snapshot = connection.execute(f"select max(as_of_date) from {relation}").fetchone()[0]
    if snapshot != config.snapshot_cutoff:
        raise ValueError(f"warehouse snapshot {snapshot} does not match {config.snapshot_cutoff}")

    grid = np.asarray(config.brier_grid_days)
    curves, supports = _km_curves(connection, relation, config, grid)
    validation = _load_frame(connection, relation, config.validation_start, config.validation_end)
    test = _load_frame(connection, relation, config.test_start, config.test_end)
    baseline_test, baseline_supported, baseline_routes = _baseline_probabilities(
        test, curves, supports, config.minimum_training_cases, len(grid)
    )
    baseline_metrics, baseline_case_ibs = evaluate_estimator(
        "kaplan_meier", test, baseline_test, baseline_supported, config
    )
    baseline_metrics["fallback_routes"] = baseline_routes

    training = _load_frame(connection, relation, config.train_start, config.train_end)
    category_maps = _category_maps(training)
    train_features = _feature_matrix(training, category_maps)
    validation_features = _feature_matrix(validation, category_maps)
    test_features = _feature_matrix(test, category_maps)
    train_matrix = _aft_matrix(train_features, training)
    validation_matrix = _aft_matrix(validation_features, validation)
    challenger = config.challenger
    parameters = {
        "objective": "survival:aft",
        "eval_metric": "aft-nloglik",
        "aft_loss_distribution": challenger.distribution,
        "aft_loss_distribution_scale": challenger.aft_loss_distribution_scale,
        "tree_method": "hist",
        "max_depth": challenger.max_depth,
        "eta": challenger.learning_rate,
        "min_child_weight": challenger.min_child_weight,
        "subsample": challenger.subsample,
        "colsample_bytree": challenger.colsample_bytree,
        "nthread": challenger.nthread,
        "seed": config.random_seed,
    }
    booster = xgb.train(
        parameters,
        train_matrix,
        num_boost_round=challenger.max_rounds,
        evals=[(validation_matrix, "validation")],
        early_stopping_rounds=challenger.early_stopping_rounds,
        verbose_eval=25,
    )
    validation_locations = np.log(
        np.maximum(
            booster.predict(validation_matrix, iteration_range=(0, booster.best_iteration + 1)), 1.0
        )
    )
    calibration = _calibrate_aft(
        validation_locations,
        _complete_outcomes(validation, grid),
        grid,
        challenger.aft_loss_distribution_scale,
    )
    test_matrix = _aft_matrix(test_features)
    test_locations = np.log(
        np.maximum(
            booster.predict(test_matrix, iteration_range=(0, booster.best_iteration + 1)), 1.0
        )
    )
    challenger_probabilities = _aft_event_probabilities(test_locations, grid, *calibration)
    challenger_supported = baseline_supported.copy()
    challenger_metrics, challenger_case_ibs = evaluate_estimator(
        "xgboost_aft", test, challenger_probabilities, challenger_supported, config
    )
    improvement = float(1.0 - challenger_case_ibs.mean() / baseline_case_ibs.mean())
    improvement_interval = _bootstrap_ibs_improvement(
        baseline_case_ibs,
        challenger_case_ibs,
        config.bootstrap_replicates,
        config.random_seed + 100,
    )
    decision = assess_shipping_policy(
        baseline_metrics,
        challenger_metrics,
        {
            "relative_ibs_improvement": improvement,
            "paired_bootstrap_95": list(improvement_interval),
        },
        config.policy,
        evidence_scope=EvidenceScope.FINAL_HOLDOUT,
    )
    governance = decision.as_dict()
    baseline_evidence = {
        "contract_version": config.version,
        "policy_id": decision.policy_id,
        "policy_digest": decision.policy_digest,
        "warehouse": warehouse.name,
        "features": list(FEATURE_COLUMNS),
        "heldout_cases": test.height,
        "metrics": baseline_metrics,
        "passes_shipping_gates": decision.baseline_passes,
    }
    (output_dir / "baseline-evaluation.json").write_text(
        json.dumps(baseline_evidence, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    report = {
        "contract_version": config.version,
        "warehouse": warehouse.name,
        "config": asdict(config),
        "cohorts": {
            "training_cases": training.height,
            "validation_cases": validation.height,
            "heldout_cases": test.height,
        },
        "features": [*FEATURE_COLUMNS, "filing_year"],
        "baseline": baseline_metrics,
        "challenger": challenger_metrics,
        "challenger_fit": {
            "best_iteration": booster.best_iteration,
            "best_validation_aft_nloglik": booster.best_score,
            "calibration_intercept": calibration[0],
            "calibration_slope": calibration[1],
            "calibration_scale": calibration[2],
        },
        "comparison": {
            "relative_ibs_improvement": improvement,
            "paired_bootstrap_95": list(improvement_interval),
        },
        "shipping_policy": governance["shipping_policy"],
        "gate_policy": {
            key: value for key, value in governance.items() if key != "shipping_policy"
        },
        "limitations": [
            "Retrospective public metadata does not determine an individual matter's duration.",
            "Evaluation covers collision-free federal civil records with supported nature codes.",
            "Administrative follow-up makes outcomes through 730 days complete for validation and held-out cohorts.",
            "No RECAP, outcome, judge, party, or post-filing feature enters the intake model.",
        ],
    }
    booster.save_model(output_dir / "xgboost-aft.ubj")
    (output_dir / "category-maps.json").write_text(
        json.dumps(category_maps, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "evaluation.json").write_text(
        json.dumps(report, indent=2, default=_json_default) + "\n", encoding="utf-8"
    )
    connection.close()
    return report
