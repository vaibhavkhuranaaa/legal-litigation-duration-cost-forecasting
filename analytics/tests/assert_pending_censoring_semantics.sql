select source_record_identifier
from {{ ref('int_fjc_record_semantics') }}
where status_code = 'S'
  and (
      event_observed
      or terminated_date is not null
      or censoring_date != source_snapshot_cutoff
      or analysis_end_date != source_snapshot_cutoff
  )
