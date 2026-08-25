select *
from {{ ref('fct_fjc_recap_match_candidates') }}
where candidate_status = 'review_eligible'
  and (recap_candidates_for_fjc != 1 or fjc_candidates_for_recap != 1)
