{{ config(contract={'enforced': true}) }}

select
    case_identifier,
    source_record_identifier,
    recap_docket_id,
    district_code,
    court_id,
    office_code,
    docket_number_core,
    filed_date,
    fjc_terminated_date,
    recap_terminated_date,
    fjc_nature_of_suit,
    recap_nature_of_suit,
    idb_data_id,
    pacer_case_id,
    recap_candidates_for_fjc,
    fjc_candidates_for_recap,
    candidate_status,
    fjc_source_digest,
    recap_source_digest,
    reconciliation_contract_version
from {{ ref('int_fjc_recap_match_candidates') }}
