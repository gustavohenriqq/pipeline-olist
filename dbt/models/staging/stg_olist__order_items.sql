with source as (
    select * from {{ source('raw', 'order_items') }}
),

renamed as (
    select
        nullif(trim(order_id), '')                 as order_id,
        cast(nullif(trim(order_item_id), '') as integer)   as order_item_id,
        nullif(trim(product_id), '')               as product_id,
        nullif(trim(seller_id), '')                as seller_id,
        cast(nullif(trim(shipping_limit_date), '') as timestamp)  as shipping_limit_at,
        cast(nullif(trim(price), '') as numeric(12, 2))           as price,
        cast(nullif(trim(freight_value), '') as numeric(12, 2))   as freight_value
    from source
)

select * from renamed
