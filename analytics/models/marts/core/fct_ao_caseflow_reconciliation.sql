{{ config(contract={'enforced': true}) }}

with ao_long as (
    select district_code, 'filed' as measure, filed as ao_value from {{ source('reconciliation_inputs', 'ao_table_c') }}
    union all
    select district_code, 'terminated' as measure, terminated as ao_value from {{ source('reconciliation_inputs', 'ao_table_c') }}
    union all
    select district_code, 'pending' as measure, pending as ao_value from {{ source('reconciliation_inputs', 'ao_table_c') }}
), fjc_long as (
    select district_code, 'filed' as measure, filed as fjc_value from {{ source('reconciliation_inputs', 'fjc_ao_population') }}
    union all
    select district_code, 'terminated' as measure, terminated as fjc_value from {{ source('reconciliation_inputs', 'fjc_ao_population') }}
    union all
    select district_code, 'pending' as measure, pending as fjc_value from {{ source('reconciliation_inputs', 'fjc_ao_population') }}
), compared as (
    select
        ao.district_code,
        ao.measure,
        cast(ao.ao_value as bigint) as ao_value,
        cast(fjc.fjc_value as bigint) as fjc_value,
        cast(fjc.fjc_value - ao.ao_value as bigint) as difference,
        abs(cast(fjc.fjc_value - ao.ao_value as double)) / nullif(cast(ao.ao_value as double), 0) as relative_difference,
        cast(case
            when ao.district_code = 'TOTAL' then {{ var('ao_total_relative_difference_threshold') }}
            else {{ var('ao_district_relative_difference_threshold') }}
        end as double) as tolerance,
        ao.district_code = 'TOTAL' as required_for_gate
    from ao_long as ao
    inner join fjc_long as fjc
        on ao.district_code = fjc.district_code and ao.measure = fjc.measure
)

select
    *,
    relative_difference <= tolerance as passed,
    case
        when difference = 0 then 'exact'
        when district_code = 'TOTAL' then 'publication_version_lag'
        when relative_difference <= tolerance then 'within_predeclared_district_tolerance'
        else 'district_definition_or_mdl_review_required'
    end as reason_code,
    case
        when passed then 'accepted'
        when required_for_gate then 'blocks_reconciliation'
        else 'retained_unresolved_district_diagnostic'
    end as disposition
from compared
