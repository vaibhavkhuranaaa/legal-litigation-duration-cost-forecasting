select source_record_identifier
from {{ ref('int_fjc_record_semantics') }}
where status_code = 'L'
  and (
      not event_observed
      or terminated_date is null
      or censoring_date is not null
      or analysis_end_date != terminated_date
  )
