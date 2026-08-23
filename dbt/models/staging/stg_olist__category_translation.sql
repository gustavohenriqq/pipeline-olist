with source as (
    select * from {{ source('raw', 'product_category_name_translation') }}
),

renamed as (
    select
        nullif(trim(product_category_name), '')          as category_name_pt,
        nullif(trim(product_category_name_english), '')  as category_name_en
    from source
)

select * from renamed
