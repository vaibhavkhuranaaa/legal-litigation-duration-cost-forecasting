{{ config(contract={'enforced': true}) }}

select
    cast(extract(year from records.filed_date) as bigint) as filing_year,
    records.district_code,
    coalesce(records.nature_of_suit_family, 'unsupported') as nature_family,
    cast(count(*) as bigint) as cohort_records,
    cast(sum(case when records.event_observed then 1 else 0 end) as bigint) as observed_terminations,
    cast(sum(case when not records.event_observed then 1 else 0 end) as bigint) as pending_records,
    cast(count(matches.source_record_identifier) as bigint) as matched_records,
    cast(sum(records.duration_days) as bigint) as followup_days,
    max(records.source_snapshot_cutoff) as as_of_date
from {{ ref('fct_federal_civil_statistical_records') }} as records
left join {{ ref('stg_promoted_fjc_recap_matches') }} as matches using (source_record_identifier)
group by
    cast(extract(year from records.filed_date) as bigint),
    records.district_code,
    coalesce(records.nature_of_suit_family, 'unsupported')
