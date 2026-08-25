with expected as (
    select
        count(*) as total_records,
        sum(case when event_observed then 1 else 0 end) as terminated_records,
        sum(case when not event_observed then 1 else 0 end) as pending_records,
        sum(case when identity_quality_status = 'canonical' then 1 else 0 end) as collision_free_records,
        sum(case when nature_of_suit_mapping_status = 'supported' then 1 else 0 end) as supported_nature_records
    from {{ ref('fct_federal_civil_statistical_records') }}
), matches as (
    select count(*) as matched_records from {{ ref('stg_promoted_fjc_recap_matches') }}
), observed as (
    select
        (select sum(total_records) from {{ ref('mart_portfolio_summary') }}) as portfolio_total,
        (select sum(terminated_records) from {{ ref('mart_portfolio_summary') }}) as portfolio_terminated,
        (select sum(pending_records) from {{ ref('mart_pending_inventory') }}) as pending_total,
        (select sum(cohort_records) from {{ ref('mart_filing_cohorts') }}) as cohort_total,
        (select sum(support_count) from {{ ref('mart_duration_summary') }}) as duration_total,
        (select count(*) from {{ ref('mart_comparable_cases') }}) as comparable_total,
        (select total_records from {{ ref('mart_data_coverage') }} where dimension_type = 'overall') as coverage_total,
        (select collision_free_records from {{ ref('mart_data_coverage') }} where dimension_type = 'overall') as coverage_collision_free,
        (select supported_nature_records from {{ ref('mart_data_coverage') }} where dimension_type = 'overall') as coverage_supported_nature,
        (select matched_records from {{ ref('mart_data_coverage') }} where dimension_type = 'overall') as coverage_matched
)

select *
from expected cross join matches cross join observed
where portfolio_total != expected.total_records
   or portfolio_terminated != expected.terminated_records
   or pending_total != expected.pending_records
   or cohort_total != expected.total_records
   or duration_total != expected.total_records
   or comparable_total != expected.collision_free_records
   or coverage_total != expected.total_records
   or coverage_collision_free != expected.collision_free_records
   or coverage_supported_nature != expected.supported_nature_records
   or coverage_matched != matches.matched_records
