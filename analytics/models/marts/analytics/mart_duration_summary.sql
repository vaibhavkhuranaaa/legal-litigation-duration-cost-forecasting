{{ config(contract={'enforced': true}) }}

select
    records.district_code,
    coalesce(records.nature_of_suit_family, 'unsupported') as nature_family,
    records.jurisdiction_code,
    records.origin_code,
    records.intake_procedural_cohort,
    cast(count(*) as bigint) as support_count,
    cast(sum(case when records.event_observed then 1 else 0 end) as bigint) as observed_terminations,
    cast(sum(case when not records.event_observed then 1 else 0 end) as bigint) as censored_records,
    cast(avg(records.duration_days) as double) as average_followup_days,
    cast(avg(case when records.event_observed then records.duration_days end) as double) as average_observed_duration_days,
    max(records.source_snapshot_cutoff) as as_of_date
from {{ ref('fct_federal_civil_statistical_records') }} as records
group by
    records.district_code,
    coalesce(records.nature_of_suit_family, 'unsupported'),
    records.jurisdiction_code,
    records.origin_code,
    records.intake_procedural_cohort
