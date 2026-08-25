select count(*) as observed
from {{ ref('stg_reconciliation_districts') }}
having count(*) != 94
