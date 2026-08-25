select source_record_identifier
from {{ ref('fct_federal_civil_statistical_records') }}
where (nature_of_suit_mapping_status = 'supported' and nature_of_suit_code is null)
   or (nature_of_suit_mapping_status = 'unsupported' and nature_of_suit_code is not null)
