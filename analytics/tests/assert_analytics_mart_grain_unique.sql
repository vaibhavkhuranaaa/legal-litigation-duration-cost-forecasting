with duplicate_grains as (
    select 'portfolio' as mart, district_code || '|' || nature_family as grain
    from {{ ref('mart_portfolio_summary') }} group by 1, 2 having count(*) != 1
    union all
    select 'cohort', cast(filing_year as {{ dbt.type_string() }}) || '|' || district_code || '|' || nature_family
    from {{ ref('mart_filing_cohorts') }} group by 1, 2 having count(*) != 1
    union all
    select 'pending', district_code || '|' || nature_family || '|' || age_band
    from {{ ref('mart_pending_inventory') }} group by 1, 2 having count(*) != 1
    union all
    select 'duration', district_code || '|' || nature_family || '|' || jurisdiction_code || '|' || origin_code
    from {{ ref('mart_duration_summary') }} group by 1, 2 having count(*) != 1
    union all
    select 'coverage', dimension_type || '|' || dimension_value
    from {{ ref('mart_data_coverage') }} group by 1, 2 having count(*) != 1
)

select * from duplicate_grains
