import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from litigation_planner.portfolio_resolution import (
    PortfolioResolutionConfig,
    _cluster_bootstrap_interval,
    mature_training_window,
    protocol_digest,
)


def test_portfolio_protocol_is_frozen_and_final_holdout_is_sealed() -> None:
    config = PortfolioResolutionConfig.from_toml(Path("config/portfolio-resolution.toml"))

    assert protocol_digest(config) == config.expected_digest
    assert config.capability_id == "portfolio_12m_resolution"
    assert config.final_holdout_start == date(2024, 4, 1)
    assert not config.final_holdout_read
    assert all(fold.assessment_end < config.final_holdout_start for fold in config.folds)


def test_training_labels_are_mature_before_prediction_origin() -> None:
    start, end = mature_training_window(date(2020, 4, 1), 365, 3)

    assert end + timedelta(days=365) == date(2020, 3, 31)
    assert end == date(2019, 4, 1)
    assert start == date(2016, 4, 2)


def test_development_protocol_rejects_final_access_and_overlap() -> None:
    config = PortfolioResolutionConfig.from_toml(Path("config/portfolio-resolution.toml"))

    with pytest.raises(ValueError, match="cannot mark the final holdout as read"):
        replace(config, final_holdout_read=True).validate()

    overlap = replace(
        config,
        folds=(*config.folds[:-1], replace(config.folds[-1], assessment_end=date(2024, 4, 1))),
    )
    with pytest.raises(ValueError, match="sealed final holdout"):
        overlap.validate()


def test_protocol_digest_detects_any_gate_change() -> None:
    config = PortfolioResolutionConfig.from_toml(Path("config/portfolio-resolution.toml"))
    changed = replace(
        config,
        gates=replace(config.gates, monthly_calibration_error=0.06),
    )

    with pytest.raises(ValueError, match="digest mismatch"):
        changed.validate()


def test_cluster_bootstrap_is_deterministic() -> None:
    counts = np.asarray([100, 150, 250], dtype=np.int64)
    events = np.asarray([50, 90, 200], dtype=np.int64)

    first = _cluster_bootstrap_interval(0.60, counts, events, 100, 42)
    second = _cluster_bootstrap_interval(0.60, counts, events, 100, 42)

    assert first == second


def test_public_development_summary_preserves_failure_and_seal() -> None:
    summary = json.loads(Path("evaluation/m7-v4-development-summary.json").read_text())

    assert summary["capability_status"] == "development_failed"
    assert summary["development_fold_pass_rate"] == 0.0
    assert not summary["final_holdout_read"]
    assert len(summary["folds"]) == 4
    assert all(not fold["passes"] for fold in summary["folds"])
