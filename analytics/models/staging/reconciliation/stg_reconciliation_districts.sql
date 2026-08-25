select
    trim(district_code) as district_code,
    trim(court_id) as court_id,
    trim(ao_label) as ao_label
from {{ source('reconciliation_inputs', 'district_mapping') }}
