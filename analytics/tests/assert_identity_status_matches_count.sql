select source_record_identifier
from {{ ref('int_fjc_identity_quality') }}
where (source_record_count = 1 and identity_quality_status != 'canonical')
   or (source_record_count > 1 and identity_quality_status != 'collision')
   or source_record_count < 1
