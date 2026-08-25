"""Deterministic synthetic staffing and budget scenarios."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class ScenarioAssumptions:
    matters: int
    horizon_months: int
    attorney_hours_per_matter_month: float
    paralegal_hours_per_matter_month: float
    attorney_rate_usd: float
    paralegal_rate_usd: float
    productive_hours_per_fte_month: float = 120.0
    low_multiplier: float = 0.8
    high_multiplier: float = 1.25

    def validate(self) -> None:
        bounded = {
            "matters": (self.matters, 1, 10_000),
            "horizon_months": (self.horizon_months, 1, 60),
            "attorney_hours_per_matter_month": (
                self.attorney_hours_per_matter_month,
                0,
                500,
            ),
            "paralegal_hours_per_matter_month": (
                self.paralegal_hours_per_matter_month,
                0,
                500,
            ),
            "attorney_rate_usd": (self.attorney_rate_usd, 0, 5_000),
            "paralegal_rate_usd": (self.paralegal_rate_usd, 0, 5_000),
            "productive_hours_per_fte_month": (
                self.productive_hours_per_fte_month,
                1,
                744,
            ),
            "low_multiplier": (self.low_multiplier, 0.1, 1.0),
            "high_multiplier": (self.high_multiplier, 1.0, 5.0),
        }
        invalid = [name for name, (value, low, high) in bounded.items() if not low <= value <= high]
        if invalid:
            raise ValueError(f"scenario assumptions outside bounds: {', '.join(invalid)}")


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def build_scenario(assumptions: ScenarioAssumptions) -> dict[str, object]:
    assumptions.validate()
    matters = Decimal(assumptions.matters)
    months = Decimal(assumptions.horizon_months)
    attorney_hours = matters * months * Decimal(str(assumptions.attorney_hours_per_matter_month))
    paralegal_hours = matters * months * Decimal(str(assumptions.paralegal_hours_per_matter_month))
    base_cost = attorney_hours * Decimal(
        str(assumptions.attorney_rate_usd)
    ) + paralegal_hours * Decimal(str(assumptions.paralegal_rate_usd))
    capacity = months * Decimal(str(assumptions.productive_hours_per_fte_month))

    def case(name: str, multiplier: float) -> dict[str, object]:
        scale = Decimal(str(multiplier))
        return {
            "name": name,
            "multiplier": multiplier,
            "attorney_hours": float(attorney_hours * scale),
            "paralegal_hours": float(paralegal_hours * scale),
            "attorney_fte": float((attorney_hours * scale / capacity).quantize(Decimal("0.01"))),
            "paralegal_fte": float((paralegal_hours * scale / capacity).quantize(Decimal("0.01"))),
            "budget_usd": _money(base_cost * scale),
        }

    return {
        "scenario_type": "synthetic",
        "observed_cost_data_used": False,
        "assumptions": asdict(assumptions),
        "cases": [
            case("low", assumptions.low_multiplier),
            case("base", 1.0),
            case("high", assumptions.high_multiplier),
        ],
        "limitation": "User-supplied sensitivity scenario; not an observed bill or real cost forecast.",
    }
