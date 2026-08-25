"""Fail-closed, capability-scoped model release policy."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class EvidenceScope(StrEnum):
    DEVELOPMENT_ONLY = "development_only"
    FINAL_HOLDOUT = "final_holdout"


@dataclass(frozen=True)
class Gates:
    calibration_error: float
    slice_calibration_error: float
    estimate_coverage: float
    challenger_ibs_improvement: float
    challenger_bootstrap_lower: float


@dataclass(frozen=True)
class CapabilityContract:
    capability_id: str
    unit_of_analysis: str
    target: str
    population: str
    horizons_days: tuple[int, ...]


@dataclass(frozen=True)
class GatePolicy:
    policy_id: str
    protocol_version: int
    capability: CapabilityContract
    thresholds: Gates
    minimum_slice_cases: int
    expected_digest: str


@dataclass(frozen=True)
class GateCheck:
    gate_id: str
    estimator: str
    observed: float | None
    threshold: float
    comparator: str
    passed: bool
    reason_code: str | None


@dataclass(frozen=True)
class ShippingDecision:
    policy_id: str
    policy_digest: str
    evidence_scope: EvidenceScope
    checks: tuple[GateCheck, ...]
    baseline_passes: bool
    challenger_passes: bool
    challenger_wins: bool
    champion: str
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        forecast_status = "ready" if self.champion != "descriptive_only" else "blocked"
        return {
            "policy_id": self.policy_id,
            "policy_digest": self.policy_digest,
            "evidence_scope": self.evidence_scope.value,
            "checks": [asdict(check) for check in self.checks],
            "shipping_policy": {
                "baseline_passes": self.baseline_passes,
                "challenger_passes": self.challenger_passes,
                "challenger_wins": self.challenger_wins,
                "champion": self.champion,
            },
            "capabilities": {
                "descriptive_analytics": {
                    "status": "ready",
                    "reason_codes": [],
                },
                "individual_duration_forecast": {
                    "status": forecast_status,
                    "reason_codes": list(self.reason_codes),
                },
            },
        }


def policy_digest(policy: GatePolicy) -> str:
    payload = {
        "policy_id": policy.policy_id,
        "protocol_version": policy.protocol_version,
        "capability": asdict(policy.capability),
        "thresholds": asdict(policy.thresholds),
        "minimum_slice_cases": policy.minimum_slice_cases,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def assert_frozen_policy(policy: GatePolicy) -> None:
    observed = policy_digest(policy)
    if observed != policy.expected_digest:
        raise ValueError(
            f"model gate policy digest mismatch: expected {policy.expected_digest}, got {observed}"
        )


def assert_nonweakening_transition(previous: GatePolicy, candidate: GatePolicy) -> None:
    if previous.capability.capability_id != candidate.capability.capability_id:
        return
    if previous.capability != candidate.capability:
        raise ValueError("changed capability contract requires a new capability identifier")
    old = previous.thresholds
    new = candidate.thresholds
    weakened = (
        new.calibration_error > old.calibration_error
        or new.slice_calibration_error > old.slice_calibration_error
        or new.estimate_coverage < old.estimate_coverage
        or new.challenger_ibs_improvement < old.challenger_ibs_improvement
        or new.challenger_bootstrap_lower < old.challenger_bootstrap_lower
        or candidate.minimum_slice_cases > previous.minimum_slice_cases
    )
    if weakened:
        raise ValueError("same-capability gate transition weakens the frozen release contract")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _check(
    gate_id: str,
    estimator: str,
    observed: Any,
    threshold: float,
    comparator: str,
) -> GateCheck:
    number = _number(observed)
    passed = number is not None and (
        number <= threshold
        if comparator == "less_than_or_equal"
        else number >= threshold
        if comparator == "greater_than_or_equal"
        else number > threshold
    )
    return GateCheck(
        gate_id=gate_id,
        estimator=estimator,
        observed=number,
        threshold=threshold,
        comparator=comparator,
        passed=passed,
        reason_code=None if passed else f"{estimator}.{gate_id}.failed",
    )


def _estimator_checks(
    estimator: str,
    metrics: Mapping[str, Any],
    policy: GatePolicy,
) -> list[GateCheck]:
    calibration = metrics.get("calibration", {})
    checks = [
        _check(
            f"calibration_{horizon}d",
            estimator,
            calibration.get(str(horizon), {}).get("error"),
            policy.thresholds.calibration_error,
            "less_than_or_equal",
        )
        for horizon in policy.capability.horizons_days
    ]
    slice_observed = metrics.get("supported_slice_maximum_error")
    if (
        not isinstance(metrics.get("supported_slice_count"), int)
        or metrics.get("supported_slice_count", 0) <= 0
    ):
        slice_observed = None
    checks.extend(
        (
            _check(
                "supported_slice_calibration",
                estimator,
                slice_observed,
                policy.thresholds.slice_calibration_error,
                "less_than_or_equal",
            ),
            _check(
                "estimate_coverage",
                estimator,
                metrics.get("estimate_coverage"),
                policy.thresholds.estimate_coverage,
                "greater_than_or_equal",
            ),
        )
    )
    eligible = metrics.get("eligible_cases")
    estimated = metrics.get("estimated_cases")
    if (
        not isinstance(eligible, int)
        or isinstance(eligible, bool)
        or eligible <= 0
        or not isinstance(estimated, int)
        or isinstance(estimated, bool)
        or estimated < 0
        or estimated > eligible
        or _number(metrics.get("estimate_coverage")) is None
        or not math.isclose(
            float(metrics["estimate_coverage"]), estimated / eligible, rel_tol=0, abs_tol=1e-9
        )
    ):
        checks.append(
            GateCheck(
                gate_id="case_accounting",
                estimator=estimator,
                observed=None,
                threshold=1.0,
                comparator="equal",
                passed=False,
                reason_code=f"{estimator}.case_accounting.failed",
            )
        )
    return checks


def assess_shipping_policy(
    baseline: Mapping[str, Any],
    challenger: Mapping[str, Any],
    comparison: Mapping[str, Any],
    policy: GatePolicy,
    *,
    evidence_scope: EvidenceScope,
) -> ShippingDecision:
    """Apply immutable gates; incomplete or development-only evidence cannot ship."""
    assert_frozen_policy(policy)
    baseline_checks = _estimator_checks("baseline", baseline, policy)
    challenger_checks = _estimator_checks("challenger", challenger, policy)
    improvement = _check(
        "ibs_improvement",
        "challenger",
        comparison.get("relative_ibs_improvement"),
        policy.thresholds.challenger_ibs_improvement,
        "greater_than_or_equal",
    )
    interval = comparison.get("paired_bootstrap_95")
    lower = interval[0] if isinstance(interval, list | tuple) and len(interval) == 2 else None
    bootstrap = _check(
        "bootstrap_lower",
        "challenger",
        lower,
        policy.thresholds.challenger_bootstrap_lower,
        "greater_than",
    )
    checks = (*baseline_checks, *challenger_checks, improvement, bootstrap)
    baseline_passes = all(check.passed for check in baseline_checks)
    challenger_passes = all(check.passed for check in challenger_checks)
    final_evidence = evidence_scope is EvidenceScope.FINAL_HOLDOUT
    challenger_wins = (
        final_evidence
        and baseline_passes
        and challenger_passes
        and improvement.passed
        and bootstrap.passed
    )
    champion = (
        "xgboost_aft"
        if challenger_wins
        else "kaplan_meier"
        if final_evidence and baseline_passes
        else "descriptive_only"
    )
    reasons = [check.reason_code for check in checks if check.reason_code]
    if not final_evidence:
        reasons.append("evidence.development_only")
    if not baseline_passes:
        reasons.append("policy.baseline_required")
    return ShippingDecision(
        policy_id=policy.policy_id,
        policy_digest=policy_digest(policy),
        evidence_scope=evidence_scope,
        checks=checks,
        baseline_passes=baseline_passes,
        challenger_passes=challenger_passes,
        challenger_wins=challenger_wins,
        champion=champion,
        reason_codes=tuple(dict.fromkeys(reasons)),
    )
