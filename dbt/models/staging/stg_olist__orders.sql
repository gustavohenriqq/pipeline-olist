with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        nullif(trim(order_id), '')                       as order_id,
        nullif(trim(customer_id), '')                    as customer_id,
        nullif(trim(order_status), '')                   as order_status,
        cast(nullif(trim(order_purchase_timestamp), '') as timestamp)        as purchased_at,
        cast(nullif(trim(order_approved_at), '') as timestamp)              as approved_at,
        cast(nullif(trim(order_delivered_carrier_date), '') as timestamp)   as delivered_carrier_at,
        cast(nullif(trim(order_delivered_customer_date), '') as timestamp)  as delivered_customer_at,
        cast(nullif(trim(order_estimated_delivery_date), '') as timestamp)  as estimated_delivery_at
    from source
)

select * from renamed
