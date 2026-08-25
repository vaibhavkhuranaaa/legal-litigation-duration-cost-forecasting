{{ config(contract={'enforced': true}) }}

select
    records.district_code,
    coalesce(records.nature_of_suit_family, 'unsupported') as nature_family,
    cast(count(*) as bigint) as total_records,
    cast(sum(case when records.identity_quality_status = 'canonical' then 1 else 0 end) as bigint) as collision_free_records,
    cast(sum(case when not records.event_observed then 1 else 0 end) as bigint) as pending_records,
    cast(sum(case when records.event_observed then 1 else 0 end) as bigint) as terminated_records,
    cast(count(matches.source_record_identifier) as bigint) as matched_records,
    cast(sum(case when records.nature_of_suit_mapping_status = 'supported' then 1 else 0 end) as bigint) as supported_nature_records,
    cast(count(matches.source_record_identifier) as double) / count(*) as match_coverage,
    cast(sum(case when not records.event_observed then 1 else 0 end) as double) / count(*) as pending_share,
    max(records.source_snapshot_cutoff) as as_of_date
from {{ ref('fct_federal_civil_statistical_records') }} as records
left join {{ ref('stg_promoted_fjc_recap_matches') }} as matches using (source_record_identifier)
group by records.district_code, coalesce(records.nature_of_suit_family, 'unsupported')
