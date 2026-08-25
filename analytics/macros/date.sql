{% macro parse_fjc_date(column_name) -%}
  {{ return(adapter.dispatch('parse_fjc_date', 'federal_civil_litigation')(column_name)) }}
{%- endmacro %}

{% macro duckdb__parse_fjc_date(column_name) -%}
  cast(try_strptime(nullif({{ column_name }}, ''), '%m/%d/%Y') as date)
{%- endmacro %}

{% macro bigquery__parse_fjc_date(column_name) -%}
  safe.parse_date('%m/%d/%Y', nullif({{ column_name }}, ''))
{%- endmacro %}

{% macro duration_days(end_date, start_date) -%}
  {{ return(adapter.dispatch('duration_days', 'federal_civil_litigation')(end_date, start_date)) }}
{%- endmacro %}

{% macro duckdb__duration_days(end_date, start_date) -%}
  date_diff('day', {{ start_date }}, {{ end_date }})
{%- endmacro %}

{% macro bigquery__duration_days(end_date, start_date) -%}
  date_diff({{ end_date }}, {{ start_date }}, day)
{%- endmacro %}
