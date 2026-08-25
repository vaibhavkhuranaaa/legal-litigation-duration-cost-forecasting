with statistical_records as (
    select count(*) as row_count from {{ ref('fct_federal_civil_statistical_records') }}
),
case_records as (
    select count(*) as row_count from {{ ref('fct_federal_civil_cases') }}
),
exception_records as (
    select count(*) as row_count from {{ ref('fct_fjc_identity_exceptions') }}
)

select
    statistical_records.row_count as statistical_rows,
    case_records.row_count as case_rows,
    exception_records.row_count as exception_rows
from statistical_records cross join case_records cross join exception_records
where statistical_records.row_count != case_records.row_count + exception_records.row_count
