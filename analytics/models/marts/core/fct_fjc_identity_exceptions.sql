{{ config(contract={'enforced': true}) }}

select
    natural_case_identifier,
    source_record_identifier,
    source_record_count,
    circuit_code,
    district_code,
    office_code,
    docket_number,
    filed_date,
    terminated_date,
    censoring_date,
    event_observed,
    nature_of_suit_raw,
    origin_code,
    disposition_code,
    source_snapshot_cutoff,
    source_digest
from {{ ref('fct_federal_civil_statistical_records') }}
where identity_quality_status = 'collision'
