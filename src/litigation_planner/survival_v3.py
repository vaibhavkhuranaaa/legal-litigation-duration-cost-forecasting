"""Development-only evaluator for the sealed M7 protocol version 3."""

from __future__ import annotations

import json
import math
import tomllib
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import polars as pl
import xgboost as xgb
from scipy.optimize import minimize
from scipy.special import expit, logit

from litigation_planner.security import SecurityBoundaryError, require_outside_repository
from litigation_planner.survival import (
    FEATURE_COLUMNS,
    SealedSurvivalProtocol,
    _aft_event_probabilities,
    _bootstrap_ibs_improvement,
    _bootstrap_interval,
    _complete_outcomes,
    _slice_calibration,
    kaplan_meier_from_counts,
)

RouteKey = tuple[str, ...]


def positive_logit_affine(
    probabilities: np.ndarray, intercept: float, log_slope: float
) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    return expit(intercept + math.exp(log_slope) * logit(clipped)).astype(np.float32)


def fit_positive_logit_affine(
    probabilities: np.ndarray, outcomes: np.ndarray
) -> tuple[float, float]:
    logits = logit(np.clip(probabilities.astype(np.float64), 1e-6, 1.0 - 1e-6))
    targets = outcomes.astype(np.float64)

    def objective(parameters: np.ndarray) -> float:
        calibrated = expit(parameters[0] + math.exp(parameters[1]) * logits)
        return float(np.mean(np.square(calibrated - targets)))

    result = minimize(
        objective,
        np.asarray([0.0, 0.0]),
        method="L-BFGS-B",
        bounds=((-5.0, 5.0), (math.log(0.25), math.log(4.0))),
    )
    if not result.success:
        raise RuntimeError(f"positive-logit calibration failed: {result.message}")
    return float(result.x[0]), float(result.x[1])


def _load_frame(
    connection: duckdb.DuckDBPyConnection,
    relation: str,
    start: date,
    end: date,
) -> pl.DataFrame:
    return connection.execute(
        f"""
        select source_record_identifier, district_code, nature_family,
               jurisdiction_code, origin_code,
               year(filed_date)::integer as filing_year,
               quarter(filed_date)::integer as filing_quarter,
               duration_days::integer as duration_days, event_observed
        from {relation}
        where filed_date between ? and ?
        order by source_record_identifier
        """,
        [start, end],
    ).pl()


def _curves(
    connection: duckdb.DuckDBPyConnection,
    relation: str,
    start: date,
    end: date,
    times: np.ndarray,
) -> tuple[dict[RouteKey, np.ndarray], dict[RouteKey, int]]:
    levels = (
        ("exact", "district_code, nature_family, jurisdiction_code, origin_code", 4),
        ("district_origin", "district_code, nature_family, origin_code", 3),
        ("district", "district_code, nature_family", 2),
        ("nature_origin", "nature_family, jurisdiction_code, origin_code", 3),
        ("nature", "nature_family", 1),
        ("global", "'all' as group_value", 1),
    )
    curves: dict[RouteKey, np.ndarray] = {}
    supports: dict[RouteKey, int] = {}
    for level, columns, width in levels:
        rows = connection.execute(
            f"""
            select {columns}, duration_days, event_observed, count(*)::bigint as records
            from {relation}
            where filed_date between ? and ? and nature_family <> 'unsupported'
            group by all
            order by all
            """,
            [start, end],
        ).fetchall()
        groups: dict[RouteKey, list[tuple[int, bool, int]]] = defaultdict(list)
        for row in rows:
            key = (level, *(str(value) for value in row[:width]))
            groups[key].append((int(row[-3]), bool(row[-2]), int(row[-1])))
        for key, values in groups.items():
            array = np.asarray(values, dtype=np.int64)
            supports[key] = int(array[:, 2].sum())
            curves[key] = kaplan_meier_from_counts(
                array[:, 0], array[:, 1].astype(bool), array[:, 2], times
            )
    return curves, supports


def _candidate_keys(
    district: object, nature: object, jurisdiction: object, origin: object
) -> tuple[tuple[str, RouteKey], ...]:
    return (
        ("exact", ("exact", str(district), str(nature), str(jurisdiction), str(origin))),
        (
            "district_nature_origin",
            ("district_origin", str(district), str(nature), str(origin)),
        ),
        ("district_nature", ("district", str(district), str(nature))),
        (
            "nature_jurisdiction_origin",
            ("nature_origin", str(nature), str(jurisdiction), str(origin)),
        ),
        ("nature", ("nature", str(nature))),
        ("global", ("global", "all")),
    )


def _route_probabilities(
    frame: pl.DataFrame,
    curves: dict[RouteKey, np.ndarray],
    supports: dict[RouteKey, int],
    minimum_training_cases: int,
    width: int,
    certified: set[RouteKey] | None = None,
) -> tuple[np.ndarray, np.ndarray, list[RouteKey | None], dict[str, int]]:
    probabilities = np.full((frame.height, width), np.nan, dtype=np.float32)
    supported = np.zeros(frame.height, dtype=bool)
    selected_keys: list[RouteKey | None] = [None] * frame.height
    route_counts: dict[str, int] = defaultdict(int)
    columns = [frame[column].to_list() for column in FEATURE_COLUMNS]
    for index, values in enumerate(zip(*columns, strict=True)):
        if values[1] == "unsupported":
            route_counts["abstain_unsupported"] += 1
            continue
        for route, key in _candidate_keys(*values):
            if supports.get(key, 0) < minimum_training_cases:
                continue
            if certified is not None and key not in certified:
                continue
            probabilities[index] = 1.0 - curves[key]
            supported[index] = True
            selected_keys[index] = key
            route_counts[route] += 1
            break
        if not supported[index]:
            route_counts["abstain_uncertified"] += 1
    return probabilities, supported, selected_keys, dict(route_counts)


def _certify_keys(
    keys: list[RouteKey | None],
    probabilities: np.ndarray,
    outcomes: np.ndarray,
    minimum_validation_cases: int,
    maximum_error: float,
) -> set[RouteKey]:
    positions: dict[RouteKey, list[int]] = defaultdict(list)
    for index, key in enumerate(keys):
        if key is not None:
            positions[key].append(index)
    certified: set[RouteKey] = set()
    for key, indices in positions.items():
        if len(indices) < minimum_validation_cases:
            continue
        errors = np.abs(probabilities[indices].mean(axis=0) - outcomes[indices].mean(axis=0))
        if float(errors.max()) <= maximum_error:
            certified.add(key)
    return certified


def _category_maps(frame: pl.DataFrame) -> dict[str, dict[str, int]]:
    return {
        column: {
            value: index for index, value in enumerate(frame[column].unique().sort().to_list())
        }
        for column in FEATURE_COLUMNS
    }


def _feature_matrix(frame: pl.DataFrame, maps: dict[str, dict[str, int]]) -> np.ndarray:
    columns = [
        frame[column]
        .replace_strict(maps[column], default=None, return_dtype=pl.Int32)
        .cast(pl.Float32)
        .to_numpy()
        for column in FEATURE_COLUMNS
    ]
    columns.extend(
        (
            frame["filing_year"].cast(pl.Float32).to_numpy(),
            frame["filing_quarter"].cast(pl.Float32).to_numpy(),
        )
    )
    return np.column_stack(columns).astype(np.float32, copy=False)


def _aft_matrix_v3(features: np.ndarray, frame: pl.DataFrame | None = None) -> xgb.DMatrix:
    matrix = xgb.DMatrix(
        features,
        feature_names=[*FEATURE_COLUMNS, "filing_year", "filing_quarter"],
        feature_types=["c", "c", "c", "c", "q", "q"],
    )
    if frame is None:
        return matrix
    durations = np.maximum(frame["duration_days"].to_numpy().astype(np.float32), 1.0)
    events = frame["event_observed"].to_numpy()
    matrix.set_float_info("label_lower_bound", durations)
    matrix.set_float_info("label_upper_bound", np.where(events, durations, np.inf))
    return matrix


def _metrics(
    name: str,
    frame: pl.DataFrame,
    probabilities: np.ndarray,
    supported: np.ndarray,
    grid: np.ndarray,
    horizons: tuple[int, ...],
    minimum_slice_cases: int,
    bootstrap_replicates: int,
    seed: int,
) -> tuple[dict[str, Any], np.ndarray]:
    outcomes_grid = _complete_outcomes(frame, grid)
    outcomes_horizons = _complete_outcomes(frame, np.asarray(horizons))
    horizon_positions = np.searchsorted(grid, horizons)
    horizon_probabilities = probabilities[:, horizon_positions]
    residuals = outcomes_horizons[supported] - horizon_probabilities[supported]
    calibration = np.abs(residuals.mean(axis=0))
    intervals = [
        _bootstrap_interval(
            residuals[:, index], bootstrap_replicates, seed + index, "absolute_mean"
        )
        for index in range(len(horizons))
    ]
    slice_maximum, slices = _slice_calibration(
        frame,
        horizon_probabilities,
        outcomes_horizons,
        supported,
        horizons,
        minimum_slice_cases,
    )
    squared = np.square(probabilities[supported] - outcomes_grid[supported])
    case_ibs = np.trapezoid(squared, grid, axis=1) / (grid[-1] - grid[0])
    return (
        {
            "name": name,
            "eligible_cases": frame.height,
            "estimated_cases": int(supported.sum()),
            "estimate_coverage": float(supported.mean()),
            "calibration": {
                str(horizon): {"error": float(error), "bootstrap_95": list(interval)}
                for horizon, error, interval in zip(horizons, calibration, intervals, strict=True)
            },
            "supported_slice_maximum_error": slice_maximum,
            "supported_slice_count": len(slices),
            "worst_supported_slices": slices[:20],
            "integrated_brier_score": float(case_ibs.mean()),
        },
        case_ibs,
    )


def _passes(metrics: dict[str, Any], gates: dict[str, Any]) -> bool:
    return (
        metrics["calibration"]["365"]["error"] <= gates["calibration_error_12m"]
        and metrics["calibration"]["730"]["error"] <= gates["calibration_error_24m"]
        and metrics["supported_slice_maximum_error"] <= gates["slice_calibration_error"]
        and metrics["estimate_coverage"] >= gates["estimate_coverage"]
    )


def run_development_evaluation(
    warehouse: Path, protocol_path: Path, output: Path
) -> dict[str, Any]:
    try:
        require_outside_repository(output)
    except SecurityBoundaryError as error:
        raise ValueError(str(error)) from error
    protocol = SealedSurvivalProtocol.from_toml(protocol_path)
    protocol.authorize_development(protocol.development_outcomes_end)
    with protocol_path.open("rb") as handle:
        config = tomllib.load(handle)
    grid = np.asarray(config["brier_grid_days"])
    horizons = tuple(config["horizons_days"])
    gates = config["gates"]
    support_config = config["support"]
    challenger_config = config["challenger"]
    fold_reports: list[dict[str, Any]] = []

    with duckdb.connect(str(warehouse), read_only=True) as connection:
        snapshot = connection.execute(
            f"select max(as_of_date) from {protocol.source_relation}"
        ).fetchone()[0]
        for fold_index, fold in enumerate(protocol.development_folds):
            protocol.authorize_development(fold.assessment_end)
            train = _load_frame(
                connection, protocol.source_relation, fold.train_start, fold.train_end
            )
            validation = _load_frame(
                connection, protocol.source_relation, fold.validation_start, fold.validation_end
            )
            assessment = _load_frame(
                connection, protocol.source_relation, fold.assessment_start, fold.assessment_end
            )
            lookback_start = date(
                fold.train_end.year - 3, fold.train_end.month, fold.train_end.day
            ) + timedelta(days=1)
            curves, supports = _curves(
                connection,
                protocol.source_relation,
                max(fold.train_start, lookback_start),
                fold.train_end,
                grid,
            )
            validation_baseline_raw, validation_supported, validation_keys, _ = (
                _route_probabilities(
                    validation,
                    curves,
                    supports,
                    support_config["minimum_training_cases"],
                    len(grid),
                )
            )
            validation_outcomes = _complete_outcomes(validation, grid)
            baseline_calibration = fit_positive_logit_affine(
                validation_baseline_raw[validation_supported],
                validation_outcomes[validation_supported],
            )
            validation_baseline = positive_logit_affine(
                validation_baseline_raw, *baseline_calibration
            )
            baseline_certified = _certify_keys(
                validation_keys,
                validation_baseline[:, np.searchsorted(grid, horizons)],
                _complete_outcomes(validation, np.asarray(horizons)),
                support_config["minimum_validation_cases"],
                support_config["maximum_validation_slice_error"],
            )
            assessment_baseline_raw, baseline_supported, _, baseline_routes = _route_probabilities(
                assessment,
                curves,
                supports,
                support_config["minimum_training_cases"],
                len(grid),
                baseline_certified,
            )
            assessment_baseline = positive_logit_affine(
                assessment_baseline_raw, *baseline_calibration
            )
            baseline_metrics, _ = _metrics(
                "kaplan_meier",
                assessment,
                assessment_baseline,
                baseline_supported,
                grid,
                horizons,
                gates["minimum_slice_cases"],
                config["bootstrap_replicates"],
                config["random_seed"] + fold_index * 1000,
            )
            baseline_metrics["fallback_routes"] = baseline_routes

            maps = _category_maps(train)
            training_matrix = _aft_matrix_v3(_feature_matrix(train, maps), train)
            validation_matrix = _aft_matrix_v3(_feature_matrix(validation, maps), validation)
            parameters = {
                "objective": "survival:aft",
                "eval_metric": "aft-nloglik",
                "aft_loss_distribution": challenger_config["distribution"],
                "aft_loss_distribution_scale": challenger_config["aft_loss_distribution_scale"],
                "tree_method": "hist",
                "max_depth": challenger_config["max_depth"],
                "eta": challenger_config["learning_rate"],
                "min_child_weight": challenger_config["min_child_weight"],
                "subsample": challenger_config["subsample"],
                "colsample_bytree": challenger_config["colsample_bytree"],
                "nthread": challenger_config["nthread"],
                "seed": config["random_seed"] + fold_index,
            }
            booster = xgb.train(
                parameters,
                training_matrix,
                num_boost_round=challenger_config["max_rounds"],
                evals=[(validation_matrix, "validation")],
                early_stopping_rounds=challenger_config["early_stopping_rounds"],
                verbose_eval=False,
            )
            validation_locations = np.log(
                np.maximum(
                    booster.predict(
                        validation_matrix, iteration_range=(0, booster.best_iteration + 1)
                    ),
                    1.0,
                )
            )
            validation_challenger_raw = _aft_event_probabilities(
                validation_locations,
                grid,
                0.0,
                1.0,
                challenger_config["aft_loss_distribution_scale"],
            )
            challenger_calibration = fit_positive_logit_affine(
                validation_challenger_raw[validation_supported],
                validation_outcomes[validation_supported],
            )
            validation_challenger = positive_logit_affine(
                validation_challenger_raw, *challenger_calibration
            )
            challenger_certified = _certify_keys(
                validation_keys,
                validation_challenger[:, np.searchsorted(grid, horizons)],
                _complete_outcomes(validation, np.asarray(horizons)),
                support_config["minimum_validation_cases"],
                support_config["maximum_validation_slice_error"],
            )
            _, challenger_supported, _, challenger_routes = _route_probabilities(
                assessment,
                curves,
                supports,
                support_config["minimum_training_cases"],
                len(grid),
                challenger_certified,
            )
            assessment_matrix = _aft_matrix_v3(_feature_matrix(assessment, maps))
            assessment_locations = np.log(
                np.maximum(
                    booster.predict(
                        assessment_matrix, iteration_range=(0, booster.best_iteration + 1)
                    ),
                    1.0,
                )
            )
            assessment_challenger_raw = _aft_event_probabilities(
                assessment_locations,
                grid,
                0.0,
                1.0,
                challenger_config["aft_loss_distribution_scale"],
            )
            assessment_challenger = positive_logit_affine(
                assessment_challenger_raw, *challenger_calibration
            )
            challenger_metrics, _ = _metrics(
                "xgboost_aft",
                assessment,
                assessment_challenger,
                challenger_supported,
                grid,
                horizons,
                gates["minimum_slice_cases"],
                config["bootstrap_replicates"],
                config["random_seed"] + fold_index * 1000 + 100,
            )
            challenger_metrics["fallback_routes"] = challenger_routes
            paired = baseline_supported & challenger_supported
            baseline_squared = np.square(
                assessment_baseline[paired] - _complete_outcomes(assessment, grid)[paired]
            )
            challenger_squared = np.square(
                assessment_challenger[paired] - _complete_outcomes(assessment, grid)[paired]
            )
            baseline_paired_ibs = np.trapezoid(baseline_squared, grid, axis=1) / (
                grid[-1] - grid[0]
            )
            challenger_paired_ibs = np.trapezoid(challenger_squared, grid, axis=1) / (
                grid[-1] - grid[0]
            )
            improvement = float(1.0 - challenger_paired_ibs.mean() / baseline_paired_ibs.mean())
            improvement_interval = _bootstrap_ibs_improvement(
                baseline_paired_ibs,
                challenger_paired_ibs,
                config["bootstrap_replicates"],
                config["random_seed"] + fold_index * 1000 + 200,
            )
            fold_reports.append(
                {
                    "fold": fold.name,
                    "source_cutoff": snapshot,
                    "cohorts": {
                        "training": train.height,
                        "validation": validation.height,
                        "assessment": assessment.height,
                    },
                    "baseline": baseline_metrics,
                    "challenger": challenger_metrics,
                    "certified_route_keys": {
                        "baseline": len(baseline_certified),
                        "challenger": len(challenger_certified),
                    },
                    "calibration_parameters": {
                        "baseline_intercept": baseline_calibration[0],
                        "baseline_positive_slope": math.exp(baseline_calibration[1]),
                        "challenger_intercept": challenger_calibration[0],
                        "challenger_positive_slope": math.exp(challenger_calibration[1]),
                    },
                    "comparison": {
                        "paired_cases": int(paired.sum()),
                        "relative_ibs_improvement": improvement,
                        "paired_bootstrap_95": list(improvement_interval),
                    },
                    "gate_decisions": {
                        "baseline_passes": _passes(baseline_metrics, gates),
                        "challenger_passes": _passes(challenger_metrics, gates),
                    },
                }
            )

    report = {
        "protocol_version": protocol.version,
        "evaluation_scope": "development_only",
        "final_holdout_read": False,
        "features": list(protocol.intake_features),
        "gates": gates,
        "folds": fold_reports,
        "development_policy_passes": {
            "baseline": all(fold["gate_decisions"]["baseline_passes"] for fold in fold_reports),
            "challenger": all(fold["gate_decisions"]["challenger_passes"] for fold in fold_reports),
        },
        "decision": "development evidence only; final holdout remains sealed",
        "limitations": [
            "Passing development folds would not establish final model readiness.",
            "FJC statistical termination is not a merits or settlement outcome.",
            "No difficult cohort is removed after outcome review.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return report
