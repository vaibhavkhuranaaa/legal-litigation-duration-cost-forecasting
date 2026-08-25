with candidates as (
    select
        fjc.case_identifier,
        fjc.source_record_identifier,
        recap.recap_docket_id,
        fjc.district_code,
        districts.court_id,
        fjc.office_code,
        fjc.docket_number as docket_number_core,
        fjc.filed_date,
        fjc.terminated_date as fjc_terminated_date,
        recap.terminated_date as recap_terminated_date,
        fjc.nature_of_suit_raw as fjc_nature_of_suit,
        recap.nature_of_suit as recap_nature_of_suit,
        recap.idb_data_id,
        recap.pacer_case_id,
        fjc.source_digest as fjc_source_digest,
        recap.source_digest as recap_source_digest,
        recap.reconciliation_contract_version
    from {{ ref('fct_federal_civil_cases') }} as fjc
    inner join {{ ref('stg_reconciliation_districts') }} as districts
        on fjc.district_code = districts.district_code
    inner join {{ ref('stg_recap_dockets') }} as recap
        on districts.court_id = recap.court_id
        and fjc.office_code = recap.office_code
        and fjc.docket_number = recap.docket_number_core
        and fjc.filed_date = recap.filed_date
), counted as (
    select
        *,
        count(*) over (partition by case_identifier) as recap_candidates_for_fjc,
        count(*) over (partition by recap_docket_id) as fjc_candidates_for_recap
    from candidates
)

select
    *,
    case
        when recap_candidates_for_fjc > 1 or fjc_candidates_for_recap > 1 then 'collision'
        when fjc_terminated_date is not null
            and recap_terminated_date is not null
            and fjc_terminated_date != recap_terminated_date then 'evidence_conflict'
        else 'review_eligible'
    end as candidate_status
from counted
