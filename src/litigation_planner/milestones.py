"""Fail-closed RECAP milestone availability contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass

EVENT_ENTRY_FIELDS = frozenset({"entry_number", "date_filed", "description"})


@dataclass(frozen=True)
class MilestoneAvailability:
    status: str
    event_updates_enabled: bool
    matched_cases: int
    eligible_cases: int
    match_coverage: float
    missing_event_fields: tuple[str, ...]
    fallback: str
    limitation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def assess_milestone_availability(
    columns: set[str], matched_cases: int, eligible_cases: int
) -> MilestoneAvailability:
    if matched_cases < 0 or eligible_cases <= 0 or matched_cases > eligible_cases:
        raise ValueError("case counts must satisfy 0 <= matched <= eligible")
    missing = tuple(sorted(EVENT_ENTRY_FIELDS.difference(columns)))
    enabled = not missing
    return MilestoneAvailability(
        status="available" if enabled else "event_unavailable",
        event_updates_enabled=enabled,
        matched_cases=matched_cases,
        eligible_cases=eligible_cases,
        match_coverage=matched_cases / eligible_cases,
        missing_event_fields=missing,
        fallback="observed_portfolio_and_intake_benchmark",
        limitation=(
            "Event-entry fields are present but require a labeled quality gate."
            if enabled
            else "Retained RECAP source contains docket metadata, not docket entries; no event "
            "family or milestone timestamp is inferred."
        ),
    )
