with source_count as (
    select count(*) as row_count from {{ source('raw_fjc', 'civil_records') }}
),
mart_count as (
    select count(*) as row_count from {{ ref('fct_federal_civil_statistical_records') }}
)

select source_count.row_count as source_rows, mart_count.row_count as mart_rows
from source_count cross join mart_count
where source_count.row_count != mart_count.row_count
