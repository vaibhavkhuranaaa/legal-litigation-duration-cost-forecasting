{% macro intake_procedural_cohort(origin_code, nature_family) -%}
case
    when {{ origin_code }} in ('6', '13') then 'multidistrict_litigation'
    when {{ nature_family }} = 'social_security' then 'social_security_review'
    when {{ origin_code }} = '1' then 'ordinary_original'
    else 'other_procedural_origin'
end
{%- endmacro %}
