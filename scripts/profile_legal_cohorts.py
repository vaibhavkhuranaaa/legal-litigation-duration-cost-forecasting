"""Profile legally meaningful M7 cohorts without reading sealed final outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from litigation_planner.survival import SealedSurvivalProtocol

COHORT_SQL = """
case
    when origin_code in ('6', '13') then 'multidistrict_litigation'
    when nature_family = 'social_security' then 'social_security_review'
    when origin_code = '1' then 'ordinary_original'
    else 'other_procedural_origin'
end
"""


def _records(cursor: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def build_profile(
    warehouse: Path,
    protocol_path: Path,
    relation: str | None = None,
) -> dict[str, object]:
    protocol = SealedSurvivalProtocol.from_toml(protocol_path)
    protocol.authorize_development(protocol.development_outcomes_end)
    source_relation = relation or protocol.source_relation
    development_end = protocol.development_outcomes_end

    with duckdb.connect(str(warehouse), read_only=True) as connection:
        source_cutoff = connection.execute(
            f"select max(as_of_date) from {source_relation}"
        ).fetchone()[0]
        followup_days = (source_cutoff - development_end).days
        if followup_days < max(protocol.horizons_days):
            raise ValueError(
                f"development cohort has {followup_days} follow-up days; "
                f"{max(protocol.horizons_days)} are required"
            )

        semantics = _records(
            connection.execute(
                f"""
                select
                    count(*)::bigint as cases,
                    count_if(event_observed)::bigint as observed_terminations,
                    count_if(not event_observed)::bigint as right_censored,
                    count_if(duration_days < 0)::bigint as negative_durations,
                    count_if(event_observed and terminated_date is null)::bigint
                        as event_without_termination,
                    count_if(not event_observed and terminated_date is not null)::bigint
                        as censor_with_termination,
                    count_if(analysis_end_date <> coalesce(terminated_date, as_of_date))::bigint
                        as analysis_end_mismatches
                from {source_relation}
                where filed_date <= ?
                """,
                [development_end],
            )
        )[0]

        cohorts = _records(
            connection.execute(
                f"""
                select
                    {COHORT_SQL} as procedural_cohort,
                    count(*)::bigint as cases,
                    avg((event_observed and duration_days <= 365)::integer)::double
                        as termination_rate_365d,
                    avg((event_observed and duration_days <= 730)::integer)::double
                        as termination_rate_730d,
                    avg((not event_observed)::integer)::double as censored_at_snapshot_share
                from {source_relation}
                where filed_date between DATE '2010-01-01' and ?
                group by 1
                order by cases desc
                """,
                [development_end],
            )
        )

        drift = _records(
            connection.execute(
                f"""
                with base as (
                    select
                        year(filed_date)::integer as filing_year,
                        event_observed,
                        duration_days,
                        district_code,
                        origin_code,
                        nature_family,
                        {COHORT_SQL} as procedural_cohort
                    from {source_relation}
                    where filed_date between DATE '2010-01-01' and ?
                ), segments as (
                    select *, 'all_cases' as segment from base
                    union all select *, 'district_29' from base where district_code = '29'
                    union all select *, 'origin_13' from base where origin_code = '13'
                    union all select *, 'personal_injury_tort' from base
                        where nature_family = 'tort_personal_injury'
                    union all select *, 'social_security' from base
                        where nature_family = 'social_security'
                    union all select *, 'multidistrict_litigation' from base
                        where procedural_cohort = 'multidistrict_litigation'
                )
                select
                    filing_year,
                    segment,
                    count(*)::bigint as cases,
                    avg((event_observed and duration_days <= 365)::integer)::double
                        as termination_rate_365d,
                    avg((event_observed and duration_days <= 730)::integer)::double
                        as termination_rate_730d
                from segments
                group by filing_year, segment
                order by filing_year, segment
                """,
                [development_end],
            )
        )

        latest_fold = protocol.development_folds[-1]
        support_routes = _records(
            connection.execute(
                f"""
                with training as (
                    select *
                    from {source_relation}
                    where filed_date between ? and ?
                      and nature_family <> 'unsupported'
                ), assessment as (
                    select *
                    from {source_relation}
                    where filed_date between ? and ?
                ), exact_support as (
                    select district_code, nature_family, jurisdiction_code, origin_code,
                           count(*)::bigint as support
                    from training group by all
                ), district_origin_support as (
                    select district_code, nature_family, origin_code,
                           count(*)::bigint as support
                    from training group by all
                ), district_support as (
                    select district_code, nature_family, count(*)::bigint as support
                    from training group by all
                ), nature_origin_support as (
                    select nature_family, jurisdiction_code, origin_code,
                           count(*)::bigint as support
                    from training group by all
                ), nature_support as (
                    select nature_family, count(*)::bigint as support
                    from training group by all
                ), routed as (
                    select
                        assessment.*,
                        case
                            when assessment.nature_family = 'unsupported' then 'abstain_unsupported'
                            when coalesce(exact_support.support, 0) >= 500 then 'exact'
                            when coalesce(district_origin_support.support, 0) >= 500
                                then 'district_nature_origin'
                            when coalesce(district_support.support, 0) >= 500
                                then 'district_nature'
                            when coalesce(nature_origin_support.support, 0) >= 500
                                then 'nature_jurisdiction_origin'
                            when coalesce(nature_support.support, 0) >= 500 then 'nature'
                            else 'global'
                        end as support_route
                    from assessment
                    left join exact_support using (
                        district_code, nature_family, jurisdiction_code, origin_code
                    )
                    left join district_origin_support using (
                        district_code, nature_family, origin_code
                    )
                    left join district_support using (district_code, nature_family)
                    left join nature_origin_support using (
                        nature_family, jurisdiction_code, origin_code
                    )
                    left join nature_support using (nature_family)
                )
                select
                    support_route,
                    count(*)::bigint as cases,
                    avg((event_observed and duration_days <= 365)::integer)::double
                        as termination_rate_365d,
                    avg((event_observed and duration_days <= 730)::integer)::double
                        as termination_rate_730d
                from routed
                group by support_route
                order by cases desc
                """,
                [
                    latest_fold.train_start,
                    latest_fold.train_end,
                    latest_fold.assessment_start,
                    latest_fold.assessment_end,
                ],
            )
        )

    return {
        "protocol_version": protocol.version,
        "outcome_access": "development_only",
        "development_outcomes_end": development_end,
        "source_cutoff": source_cutoff,
        "complete_followup_days": followup_days,
        "outcome_definition": "fjc_statistical_termination",
        "duration_and_censoring_semantics": semantics,
        "procedural_cohorts": cohorts,
        "calendar_drift": drift,
        "latest_development_fold_support_routes": support_routes,
        "limitations": [
            "FJC statistical termination is not a merits, settlement, or client-work outcome.",
            "MDL is a governed descriptive cohort and is not removed from protocol version 3.",
            "Support routes measure training support, not estimator calibration or readiness.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path("config/survival-v3.toml"))
    parser.add_argument("--relation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_profile(args.warehouse, args.protocol, args.relation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
