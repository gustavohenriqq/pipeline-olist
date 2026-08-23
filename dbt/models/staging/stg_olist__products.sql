with source as (
    select * from {{ source('raw', 'products') }}
),

translation as (
    select * from {{ ref('stg_olist__category_translation') }}
),

renamed as (
    select
        nullif(trim(product_id), '')                     as product_id,
        nullif(trim(product_category_name), '')          as category_name_pt,
        cast(nullif(trim(product_name_lenght), '') as integer)         as name_length,
        cast(nullif(trim(product_description_lenght), '') as integer)  as description_length,
        cast(nullif(trim(product_photos_qty), '') as integer)         as photos_qty,
        cast(nullif(trim(product_weight_g), '') as numeric)           as weight_g,
        cast(nullif(trim(product_length_cm), '') as numeric)          as length_cm,
        cast(nullif(trim(product_height_cm), '') as numeric)          as height_cm,
        cast(nullif(trim(product_width_cm), '') as numeric)           as width_cm
    from source
)

select
    r.product_id,
    r.category_name_pt,
    -- Se nao houver traducao, cai para a categoria em portugues.
    coalesce(t.category_name_en, r.category_name_pt)  as category_name_en,
    r.name_length,
    r.description_length,
    r.photos_qty,
    r.weight_g,
    r.length_cm,
    r.height_cm,
    r.width_cm
from renamed r
left join translation t
    on r.category_name_pt = t.category_name_pt
