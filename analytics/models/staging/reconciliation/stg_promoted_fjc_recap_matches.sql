select
    cast(case_identifier as {{ dbt.type_string() }}) as case_identifier,
    cast(source_record_identifier as {{ dbt.type_string() }}) as source_record_identifier,
    cast(recap_docket_id as {{ dbt.type_string() }}) as recap_docket_id,
    cast(match_rule_id as {{ dbt.type_string() }}) as match_rule_id,
    cast(review_completed_at_utc as timestamp) as review_completed_at_utc
from {{ source('reconciliation_inputs', 'promoted_matches') }}
