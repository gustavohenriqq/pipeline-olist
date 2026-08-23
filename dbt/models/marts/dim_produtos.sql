-- Dimensao de produtos, com categoria em portugues e ingles.
with products as (
    select * from {{ ref('stg_olist__products') }}
)

select
    {{ gera_sk(['product_id']) }} as produto_sk,
    product_id,
    category_name_pt            as categoria_pt,
    category_name_en            as categoria_en,
    photos_qty                  as qtd_fotos,
    weight_g                    as peso_g,
    length_cm                   as comprimento_cm,
    height_cm                   as altura_cm,
    width_cm                    as largura_cm,
    -- Volume em cm3 ajuda a analisar custo de frete por tamanho.
    (length_cm * height_cm * width_cm) as volume_cm3
from products
