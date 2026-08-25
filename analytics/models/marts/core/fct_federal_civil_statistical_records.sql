{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert' if target.type == 'duckdb' else 'merge',
        unique_key='source_record_identifier',
        on_schema_change='fail',
        contract={'enforced': true}
    )
}}

with records as (
    select * from {{ ref('int_fjc_identity_quality') }}
),
mapping as (
    select * from {{ ref('int_nature_of_suit_mapping') }}
)

select
    records.source_record_identifier,
    records.natural_case_identifier,
    records.source_row_number,
    records.circuit_code,
    records.district_code,
    records.office_code,
    records.docket_number,
    records.filed_date,
    records.filed_date_used_by_ao,
    records.terminated_date,
    records.termination_date_used_by_ao,
    records.censoring_date,
    records.analysis_end_date,
    records.duration_days,
    records.event_observed,
    records.nature_of_suit_raw,
    records.title_raw,
    records.section_raw,
    records.subsection_raw,
    records.jury_demand_raw,
    records.mdl_docket_raw,
    mapping.canonical_code as nature_of_suit_code,
    mapping.label as nature_of_suit_label,
    mapping.family as nature_of_suit_family,
    case when mapping.raw_code is null then 'unsupported' else 'supported' end as nature_of_suit_mapping_status,
    mapping.rule_version as nature_of_suit_rule_version,
    records.jurisdiction_code,
    records.origin_code,
    {{ intake_procedural_cohort('records.origin_code', "coalesce(mapping.family, 'unsupported')") }} as intake_procedural_cohort,
    records.procedural_progress_code,
    records.disposition_code,
    records.identity_quality_status,
    records.source_record_count,
    records.statistical_year,
    records.source_snapshot_cutoff,
    records.source_digest,
    records.raw_contract_version
from records
left join mapping on records.nature_of_suit_raw = mapping.raw_code
{% if is_incremental() %}
where records.source_digest not in (select distinct source_digest from {{ this }})
{% endif %}
