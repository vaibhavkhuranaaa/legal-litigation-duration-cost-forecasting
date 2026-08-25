{{
    config(
        enabled=var('enable_contract_failure_fixture', false),
        materialized='table',
        contract={'enforced': true}
    )
}}

select 'deliberate contract violation' as must_be_boolean
