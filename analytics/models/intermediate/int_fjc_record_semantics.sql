with records as (
    select * from {{ ref('stg_fjc_civil_records') }}
)

select
    concat(source_digest, ':', cast(source_row_number as {{ dbt.type_string() }})) as source_record_identifier,
    concat(circuit_code, '|', district_code, '|', office_code, '|', docket_number) as natural_case_identifier,
    records.*,
    status_code = 'L' as event_observed,
    case when status_code = 'L' then termination_date_source end as terminated_date,
    case when status_code = 'S' then source_snapshot_cutoff end as censoring_date,
    case
        when status_code = 'L' then termination_date_source
        else source_snapshot_cutoff
    end as analysis_end_date,
    {{ duration_days(
        "case when status_code = 'L' then termination_date_source else source_snapshot_cutoff end",
        'filed_date'
    ) }} as duration_days
from records
