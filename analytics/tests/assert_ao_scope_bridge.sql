select *
from {{ ref('fct_ao_scope_bridge') }}
where (measure = 'filed' and excluded_or_quarantined_records != 0)
   or (measure = 'terminated' and excluded_or_quarantined_records != 61)
   or (measure = 'pending' and excluded_or_quarantined_records != 4896)
