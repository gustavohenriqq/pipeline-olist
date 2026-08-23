with source as (
    select * from {{ source('raw', 'order_payments') }}
),

renamed as (
    select
        nullif(trim(order_id), '')                       as order_id,
        cast(nullif(trim(payment_sequential), '') as integer)     as payment_sequential,
        nullif(trim(payment_type), '')                   as payment_type,
        cast(nullif(trim(payment_installments), '') as integer)   as installments,
        cast(nullif(trim(payment_value), '') as numeric(12, 2))   as payment_value
    from source
)

select * from renamed
