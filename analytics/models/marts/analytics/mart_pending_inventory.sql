{{ config(contract={'enforced': true}) }}

with pending as (
    select
        records.*,
        matches.source_record_identifier is not null as has_recap_match,
        case
            when records.duration_days < 365 then 'under_1_year'
            when records.duration_days < 730 then '1_to_2_years'
            when records.duration_days < 1825 then '2_to_5_years'
            else '5_years_or_more'
        end as age_band
    from {{ ref('fct_federal_civil_statistical_records') }} as records
    left join {{ ref('stg_promoted_fjc_recap_matches') }} as matches using (source_record_identifier)
    where not records.event_observed
)

select
    district_code,
    coalesce(nature_of_suit_family, 'unsupported') as nature_family,
    age_band,
    cast(count(*) as bigint) as pending_records,
    cast(sum(case when has_recap_match then 1 else 0 end) as bigint) as matched_pending_records,
    cast(avg(duration_days) as double) as average_age_days,
    max(source_snapshot_cutoff) as as_of_date
from pending
group by district_code, coalesce(nature_of_suit_family, 'unsupported'), age_band
