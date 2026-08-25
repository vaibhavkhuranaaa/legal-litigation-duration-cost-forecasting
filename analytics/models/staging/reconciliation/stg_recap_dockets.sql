select
    cast(recap_docket_id as {{ dbt.type_string() }}) as recap_docket_id,
    trim(court_id) as court_id,
    trim(office_code) as office_code,
    trim(docket_number_core) as docket_number_core,
    filed_date,
    terminated_date,
    trim(nature_of_suit) as nature_of_suit,
    trim(jurisdiction_type) as jurisdiction_type,
    nullif(trim(idb_data_id), '') as idb_data_id,
    nullif(trim(pacer_case_id), '') as pacer_case_id,
    cast(source_row_number as bigint) as source_row_number,
    source_snapshot_cutoff,
    source_digest,
    cast(reconciliation_contract_version as bigint) as reconciliation_contract_version
from {{ source('reconciliation_inputs', 'recap_dockets') }}
