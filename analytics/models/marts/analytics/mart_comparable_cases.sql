{{ config(contract={'enforced': true}) }}

select
    cases.case_identifier,
    cases.source_record_identifier,
    cases.district_code,
    cases.filed_date,
    cases.terminated_date,
    cases.analysis_end_date,
    cases.duration_days,
    cases.event_observed,
    coalesce(cases.nature_of_suit_family, 'unsupported') as nature_family,
    cases.jurisdiction_code,
    cases.origin_code,
    cases.intake_procedural_cohort,
    cases.title_raw as filing_title_code,
    cases.section_raw as filing_section_code,
    cases.subsection_raw as filing_subsection_code,
    cases.jury_demand_raw as snapshot_jury_demand_code,
    cases.mdl_docket_raw as snapshot_mdl_docket_code,
    'fjc_statistical_termination' as outcome_definition,
    matches.recap_docket_id is not null as has_recap_match,
    cast(count(*) over (
        partition by
            cases.district_code,
            coalesce(cases.nature_of_suit_family, 'unsupported'),
            cases.jurisdiction_code,
            cases.origin_code
    ) as bigint) as comparable_group_support_count,
    cases.source_snapshot_cutoff as as_of_date
from {{ ref('fct_federal_civil_cases') }} as cases
left join {{ ref('stg_promoted_fjc_recap_matches') }} as matches using (source_record_identifier)
