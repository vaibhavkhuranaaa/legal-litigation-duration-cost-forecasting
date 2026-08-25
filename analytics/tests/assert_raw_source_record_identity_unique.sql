select
    source_snapshot_cutoff,
    source_digest,
    raw_contract_version,
    source_row_number,
    count(*) as record_count
from {{ source('raw_fjc', 'civil_records') }}
group by source_snapshot_cutoff, source_digest, raw_contract_version, source_row_number
having count(*) > 1
