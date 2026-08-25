{{ config(contract={'enforced': true}) }}

with population as (
    select
        records.district_code,
        cast(extract(year from records.filed_date) as {{ dbt.type_string() }}) as filing_year,
        coalesce(records.nature_of_suit_family, 'unsupported') as nature_family,
        records.intake_procedural_cohort,
        records.identity_quality_status = 'canonical' as collision_free,
        records.nature_of_suit_mapping_status = 'supported' as supported_nature,
        matches.source_record_identifier is not null as matched
    from {{ ref('fct_federal_civil_statistical_records') }} as records
    left join {{ ref('stg_promoted_fjc_recap_matches') }} as matches using (source_record_identifier)
), dimensions as (
    select 'overall' as dimension_type, 'all' as dimension_value, * from population
    union all
    select 'district', district_code, * from population
    union all
    select 'filing_year', filing_year, * from population
    union all
    select 'nature_family', nature_family, * from population
    union all
    select 'procedural_cohort', intake_procedural_cohort, * from population
)

select
    dimension_type,
    dimension_value,
    cast(count(*) as bigint) as total_records,
    cast(sum(case when collision_free then 1 else 0 end) as bigint) as collision_free_records,
    cast(sum(case when supported_nature then 1 else 0 end) as bigint) as supported_nature_records,
    cast(sum(case when matched then 1 else 0 end) as bigint) as matched_records,
    cast(sum(case when matched then 1 else 0 end) as double) / count(*) as match_coverage
from dimensions
group by dimension_type, dimension_value
