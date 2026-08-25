import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from litigation_planner.gate_policy import (
    EvidenceScope,
    assert_frozen_policy,
    assert_nonweakening_transition,
    assess_shipping_policy,
)
from litigation_planner.survival import (
    FEATURE_COLUMNS,
    SurvivalConfig,
    _complete_outcomes,
    _slice_calibration,
    kaplan_meier_from_counts,
    run_survival_evaluation,
)


def test_survival_contract_is_time_ordered_and_complete() -> None:
    config = SurvivalConfig.from_toml(Path("config/survival.toml"))

    assert config.train_end < config.validation_start
    assert config.validation_end < config.test_start
    assert config.test_end < config.snapshot_cutoff
    assert config.horizons_days == (365, 730)
    assert FEATURE_COLUMNS == (
        "district_code",
        "nature_family",
        "jurisdiction_code",
        "origin_code",
    )


def test_kaplan_meier_preserves_censoring_and_event_timing() -> None:
    curve = kaplan_meier_from_counts(
        np.asarray([1, 2, 3]),
        np.asarray([True, False, True]),
        np.asarray([1, 1, 1]),
        np.asarray([0, 1, 2, 3]),
    )

    assert curve == pytest.approx([1.0, 2 / 3, 2 / 3, 0.0])


def test_complete_outcomes_reject_early_censoring() -> None:
    frame = pl.DataFrame({"duration_days": [300], "event_observed": [False]})

    with pytest.raises(ValueError, match="censoring"):
        _complete_outcomes(frame, np.asarray([365]))


def test_slice_calibration_uses_only_supported_slices() -> None:
    frame = pl.DataFrame(
        {
            "district_code": ["A", "A", "B"],
            "nature_family": ["x", "x", "y"],
            "jurisdiction_code": ["1", "1", "2"],
            "origin_code": ["1", "1", "2"],
        }
    )
    probabilities = np.asarray([[0.5, 0.5], [0.5, 0.5], [0.0, 0.0]])
    outcomes = np.asarray([[True, True], [False, False], [True, True]])

    maximum, records = _slice_calibration(
        frame,
        probabilities,
        outcomes,
        np.asarray([True, True, False]),
        (365, 730),
        minimum_cases=2,
    )

    assert maximum == 0.0
    assert records
    assert all(record["cases"] == 2 for record in records)


def test_config_snapshot_matches_declared_source_cutoff() -> None:
    config = SurvivalConfig.from_toml(Path("config/survival.toml"))

    assert config.snapshot_cutoff == date(2026, 3, 31)


def test_survival_evaluation_rejects_public_output() -> None:
    with pytest.raises(ValueError, match="outside public repository"):
        run_survival_evaluation(
            Path("missing.duckdb"), Path("config/survival.toml"), Path("tmp/model-output")
        )


def _metrics(calibration_365: float, calibration_730: float, slice_error: float) -> dict:
    return {
        "eligible_cases": 329_617,
        "estimated_cases": 329_617,
        "estimate_coverage": 1.0,
        "calibration": {
            "365": {"error": calibration_365},
            "730": {"error": calibration_730},
        },
        "supported_slice_maximum_error": slice_error,
        "supported_slice_count": 113,
    }


def test_policy_as_code_reproduces_v2_descriptive_only_decision() -> None:
    config = SurvivalConfig.from_toml(Path("config/survival.toml"))
    decision = assess_shipping_policy(
        _metrics(0.048584990203380585, 0.1147201731801033, 0.7781025598530199),
        _metrics(0.017400313168764114, 0.08093826472759247, 0.525208009291115),
        {
            "relative_ibs_improvement": 0.13766216519804508,
            "paired_bootstrap_95": [0.13633829793121668, 0.13905992590121083],
        },
        config.policy,
        evidence_scope=EvidenceScope.FINAL_HOLDOUT,
    )

    assert decision.champion == "descriptive_only"
    assert not decision.baseline_passes
    assert not decision.challenger_passes
    assert not decision.challenger_wins
    assert "baseline.calibration_730d.failed" in decision.reason_codes
    assert "challenger.supported_slice_calibration.failed" in decision.reason_codes


def test_development_evidence_cannot_promote_a_passing_model() -> None:
    config = SurvivalConfig.from_toml(Path("config/survival.toml"))
    passing = _metrics(0.01, 0.02, 0.03)
    decision = assess_shipping_policy(
        passing,
        passing,
        {"relative_ibs_improvement": 0.10, "paired_bootstrap_95": [0.08, 0.12]},
        config.policy,
        evidence_scope=EvidenceScope.DEVELOPMENT_ONLY,
    )

    assert decision.baseline_passes
    assert decision.challenger_passes
    assert decision.champion == "descriptive_only"
    assert decision.reason_codes == ("evidence.development_only",)


def test_policy_digest_detects_post_hoc_threshold_change() -> None:
    policy = SurvivalConfig.from_toml(Path("config/survival.toml")).policy
    changed = replace(
        policy,
        thresholds=replace(policy.thresholds, slice_calibration_error=0.11),
    )

    with pytest.raises(ValueError, match="digest mismatch"):
        assert_frozen_policy(changed)
    with pytest.raises(ValueError, match="weakens"):
        assert_nonweakening_transition(policy, replace(changed, expected_digest="changed"))

    redefined = replace(
        policy,
        capability=replace(policy.capability, horizons_days=(365,)),
    )
    with pytest.raises(ValueError, match="new capability identifier"):
        assert_nonweakening_transition(policy, redefined)


def test_policy_fails_closed_on_missing_or_nonfinite_metrics() -> None:
    config = SurvivalConfig.from_toml(Path("config/survival.toml"))
    incomplete = _metrics(0.01, float("nan"), 0.03)
    incomplete["supported_slice_count"] = 0
    decision = assess_shipping_policy(
        incomplete,
        _metrics(0.01, 0.02, 0.03),
        {"relative_ibs_improvement": 0.10, "paired_bootstrap_95": [0.08, 0.12]},
        config.policy,
        evidence_scope=EvidenceScope.FINAL_HOLDOUT,
    )

    assert decision.champion == "descriptive_only"
    assert "baseline.calibration_730d.failed" in decision.reason_codes
    assert "baseline.supported_slice_calibration.failed" in decision.reason_codes


def test_survival_splits_must_be_strictly_non_overlapping() -> None:
    config = SurvivalConfig.from_toml(Path("config/survival.toml"))

    with pytest.raises(ValueError, match="strictly non-overlapping"):
        replace(config, validation_start=config.train_end).validate()


def test_public_release_decision_is_locked_to_current_policy() -> None:
    config = SurvivalConfig.from_toml(Path("config/survival.toml"))
    evidence = json.loads(Path("evaluation/m7-release-decision.json").read_text())

    assert evidence["policy_digest"] == config.policy.expected_digest
    assert evidence["shipping_policy"]["champion"] == "descriptive_only"
    assert evidence["capabilities"]["descriptive_analytics"]["status"] == "ready"
    assert evidence["capabilities"]["individual_duration_forecast"]["status"] == "blocked"
