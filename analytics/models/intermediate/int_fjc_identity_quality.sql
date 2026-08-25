with identity_counts as (
    select
        natural_case_identifier,
        count(*) as source_record_count
    from {{ ref('int_fjc_record_semantics') }}
    group by natural_case_identifier
)

select
    records.*,
    identity_counts.source_record_count,
    case
        when identity_counts.source_record_count = 1 then 'canonical'
        else 'collision'
    end as identity_quality_status
from {{ ref('int_fjc_record_semantics') }} as records
inner join identity_counts using (natural_case_identifier)
