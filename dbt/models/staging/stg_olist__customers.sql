with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        nullif(trim(customer_id), '')                as customer_id,
        nullif(trim(customer_unique_id), '')         as customer_unique_id,
        cast(nullif(trim(customer_zip_code_prefix), '') as integer)  as zip_code_prefix,
        initcap(nullif(trim(customer_city), ''))     as city,
        upper(nullif(trim(customer_state), ''))      as state
    from source
)

select * from renamed
