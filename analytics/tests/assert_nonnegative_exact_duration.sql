select source_record_identifier
from {{ ref('int_fjc_record_semantics') }}
where duration_days < 0
   or duration_days != {{ duration_days('analysis_end_date', 'filed_date') }}
