with source_count as (
    select count(*) as row_count from {{ source('raw_fjc', 'civil_records') }}
),
staging_count as (
    select count(*) as row_count from {{ ref('stg_fjc_civil_records') }}
)

select source_count.row_count as source_rows, staging_count.row_count as staging_rows
from source_count cross join staging_count
where source_count.row_count != staging_count.row_count
