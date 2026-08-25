select *
from {{ ref('fct_ao_caseflow_reconciliation') }}
where required_for_gate and not passed
