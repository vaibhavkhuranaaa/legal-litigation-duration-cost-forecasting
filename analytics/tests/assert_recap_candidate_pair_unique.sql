select case_identifier, recap_docket_id, count(*) as observed
from {{ ref('fct_fjc_recap_match_candidates') }}
group by 1, 2
having count(*) != 1
