import tomllib
from datetime import date
from pathlib import Path

import pytest

from litigation_planner.survival import (
    ProtocolAuthorizationError,
    SealedSurvivalProtocol,
)


def test_protocol_v3_is_sealed_chronological_and_complete() -> None:
    with Path("config/survival-v3.toml").open("rb") as handle:
        protocol = tomllib.load(handle)

    cutoff = date.fromisoformat(protocol["required_snapshot_cutoff"])
    development_end = date.fromisoformat(protocol["development_outcomes_end"])
    holdout_start = date.fromisoformat(protocol["final_holdout_start"])
    holdout_end = date.fromisoformat(protocol["final_holdout_end"])

    assert protocol["version"] == 3
    assert protocol["status"] == "sealed_pending_source"
    assert development_end < holdout_start <= holdout_end < cutoff
    assert (cutoff - holdout_end).days >= max(protocol["horizons_days"])
    assert protocol["final_score_attempts"] == 1


def test_protocol_v3_rolling_folds_do_not_touch_final_holdout() -> None:
    with Path("config/survival-v3.toml").open("rb") as handle:
        protocol = tomllib.load(handle)

    development_end = date.fromisoformat(protocol["development_outcomes_end"])
    holdout_start = date.fromisoformat(protocol["final_holdout_start"])
    for fold in protocol["development_fold"]:
        train_end = date.fromisoformat(fold["train_end"])
        validation_start = date.fromisoformat(fold["validation_start"])
        validation_end = date.fromisoformat(fold["validation_end"])
        assessment_start = date.fromisoformat(fold["assessment_start"])
        assessment_end = date.fromisoformat(fold["assessment_end"])
        assert train_end < validation_start <= validation_end < assessment_start
        assert assessment_start <= assessment_end <= development_end < holdout_start


def test_protocol_v3_preserves_features_and_release_gates() -> None:
    with Path("config/survival-v3.toml").open("rb") as handle:
        protocol = tomllib.load(handle)

    gates = protocol["gates"]
    assert gates == {
        "calibration_error_12m": 0.05,
        "calibration_error_24m": 0.05,
        "slice_calibration_error": 0.10,
        "minimum_slice_cases": 200,
        "estimate_coverage": 0.80,
        "challenger_ibs_improvement": 0.05,
        "challenger_bootstrap_lower": 0.0,
    }
    assert set(protocol["intake_features"]).isdisjoint(protocol["forbidden_features"])
    assert protocol["baseline"]["estimator"] == "kaplan_meier"
    assert protocol["challenger"]["estimator"] == "xgboost_aft"
    assert protocol["support"]["unseen_category_behavior"] == "abstain"


def test_protocol_v3_refuses_current_snapshot_before_final_outcomes() -> None:
    protocol = SealedSurvivalProtocol.from_toml(Path("config/survival-v3.toml"))

    with pytest.raises(ProtocolAuthorizationError, match="earlier than required cutoff"):
        protocol.authorize_final(date(2026, 3, 31))


def test_protocol_v3_authorizes_only_frozen_development_window() -> None:
    protocol = SealedSurvivalProtocol.from_toml(Path("config/survival-v3.toml"))

    protocol.authorize_development(date(2024, 3, 31))
    with pytest.raises(ProtocolAuthorizationError, match="exceeds frozen development end"):
        protocol.authorize_development(date(2024, 4, 1))


def test_protocol_v3_allows_one_qualifying_final_score() -> None:
    protocol = SealedSurvivalProtocol.from_toml(Path("config/survival-v3.toml"))

    protocol.authorize_final(date(2026, 6, 30), completed_attempts=0)
    with pytest.raises(ProtocolAuthorizationError, match="allowance is exhausted"):
        protocol.authorize_final(date(2026, 6, 30), completed_attempts=1)
