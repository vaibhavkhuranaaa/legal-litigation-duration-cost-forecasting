{{ config(contract={'enforced': true}) }}

select
    natural_case_identifier as case_identifier,
    source_record_identifier,
    circuit_code,
    district_code,
    office_code,
    docket_number,
    filed_date,
    terminated_date,
    censoring_date,
    analysis_end_date,
    duration_days,
    event_observed,
    nature_of_suit_raw,
    title_raw,
    section_raw,
    subsection_raw,
    jury_demand_raw,
    mdl_docket_raw,
    nature_of_suit_code,
    nature_of_suit_label,
    nature_of_suit_family,
    nature_of_suit_mapping_status,
    jurisdiction_code,
    origin_code,
    intake_procedural_cohort,
    source_snapshot_cutoff,
    source_digest
from {{ ref('fct_federal_civil_statistical_records') }}
where identity_quality_status = 'canonical'
