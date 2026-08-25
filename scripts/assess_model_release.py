"""Reassess aggregate model evidence against the frozen release policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from litigation_planner.gate_policy import EvidenceScope, assess_shipping_policy
from litigation_planner.survival import SurvivalConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/survival.toml"))
    parser.add_argument(
        "--evidence-scope",
        choices=[scope.value for scope in EvidenceScope],
        default=EvidenceScope.DEVELOPMENT_ONLY.value,
    )
    args = parser.parse_args()
    report = json.loads(args.evaluation.read_text(encoding="utf-8"))
    config = SurvivalConfig.from_toml(args.config)
    decision = assess_shipping_policy(
        report.get("baseline", {}),
        report.get("challenger", {}),
        report.get("comparison", {}),
        config.policy,
        evidence_scope=EvidenceScope(args.evidence_scope),
    )
    output = {
        "contract_version": report.get("contract_version"),
        "source_evidence": "aggregate_metrics_only",
        **decision.as_dict(),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
