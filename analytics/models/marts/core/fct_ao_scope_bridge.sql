{{ config(contract={'enforced': true}) }}

with product as (
    select
        sum(case when filed_date_used_by_ao between cast('2025-04-01' as date) and cast('2026-03-31' as date) then 1 else 0 end) as filed,
        sum(case when termination_date_used_by_ao between cast('2025-04-01' as date) and cast('2026-03-31' as date) then 1 else 0 end) as terminated,
        sum(case when not event_observed then 1 else 0 end) as pending
    from {{ ref('fct_federal_civil_statistical_records') }}
), complete_snapshot as (
    select filed, terminated, pending
    from {{ source('reconciliation_inputs', 'fjc_ao_population') }}
    where district_code = 'TOTAL'
), bridge as (
    select 'filed' as measure, complete_snapshot.filed as complete_snapshot_value, product.filed as product_value from complete_snapshot cross join product
    union all
    select 'terminated', complete_snapshot.terminated, product.terminated from complete_snapshot cross join product
    union all
    select 'pending', complete_snapshot.pending, product.pending from complete_snapshot cross join product
)

select
    measure,
    cast(complete_snapshot_value as bigint) as complete_snapshot_value,
    cast(product_value as bigint) as product_value,
    cast(complete_snapshot_value - product_value as bigint) as excluded_or_quarantined_records,
    case
        when measure = 'pending' then 'pre_2010_product_scope_exclusion'
        when measure = 'terminated' then 'structural_quarantine_and_product_scope'
        else 'no_scope_difference'
    end as explanation
from bridge
