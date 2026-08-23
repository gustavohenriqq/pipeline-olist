with source as (
    select * from {{ source('raw', 'sellers') }}
),

renamed as (
    select
        nullif(trim(seller_id), '')                as seller_id,
        cast(nullif(trim(seller_zip_code_prefix), '') as integer)  as zip_code_prefix,
        initcap(nullif(trim(seller_city), ''))     as city,
        upper(nullif(trim(seller_state), ''))      as state
    from source
)

select * from renamed
