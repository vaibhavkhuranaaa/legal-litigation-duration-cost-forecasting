{{ config(contract={'enforced': true}) }}

select
    canonical_code as nature_of_suit_code,
    label as nature_of_suit_label,
    family as nature_of_suit_family,
    codebook_as_of_date,
    rule_version
from {{ ref('int_nature_of_suit_mapping') }}
