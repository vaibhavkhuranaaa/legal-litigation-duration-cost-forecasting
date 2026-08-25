select
    source_record_identifier,
    origin_code,
    coalesce(nature_of_suit_family, 'unsupported') as nature_family,
    intake_procedural_cohort
from {{ ref('fct_federal_civil_statistical_records') }}
where intake_procedural_cohort <> case
    when origin_code in ('6', '13') then 'multidistrict_litigation'
    when coalesce(nature_of_suit_family, 'unsupported') = 'social_security'
        then 'social_security_review'
    when origin_code = '1' then 'ordinary_original'
    else 'other_procedural_origin'
end
