import pytest

from litigation_planner.scenarios import ScenarioAssumptions, build_scenario


def assumptions() -> ScenarioAssumptions:
    return ScenarioAssumptions(
        matters=10,
        horizon_months=6,
        attorney_hours_per_matter_month=5,
        paralegal_hours_per_matter_month=8,
        attorney_rate_usd=300,
        paralegal_rate_usd=125,
    )


def test_scenario_is_deterministic_and_explicitly_synthetic() -> None:
    first = build_scenario(assumptions())

    assert first == build_scenario(assumptions())
    assert first["scenario_type"] == "synthetic"
    assert first["observed_cost_data_used"] is False
    assert [case["budget_usd"] for case in first["cases"]] == [120000.0, 150000.0, 187500.0]


def test_scenario_rejects_unbounded_inputs() -> None:
    with pytest.raises(ValueError, match="matters"):
        build_scenario(ScenarioAssumptions(**{**assumptions().__dict__, "matters": 0}))
