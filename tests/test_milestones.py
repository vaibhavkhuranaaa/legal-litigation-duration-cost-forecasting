from litigation_planner.milestones import assess_milestone_availability


def test_docket_metadata_refuses_event_updates() -> None:
    result = assess_milestone_availability(
        {"id", "date_filed", "date_terminated", "docket_number"}, 40, 100
    )

    assert result.status == "event_unavailable"
    assert not result.event_updates_enabled
    assert result.match_coverage == 0.4
    assert result.missing_event_fields == ("description", "entry_number")


def test_event_contract_requires_valid_case_counts() -> None:
    try:
        assess_milestone_availability(set(), 2, 1)
    except ValueError as error:
        assert "0 <= matched <= eligible" in str(error)
    else:
        raise AssertionError("invalid case counts were accepted")
