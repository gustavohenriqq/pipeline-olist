-- Agrega os itens em uma linha por pedido (valor de produtos, frete, contagens).
with itens as (
    select * from {{ ref('stg_olist__order_items') }}
)

select
    order_id,
    count(*)                          as qtd_itens,
    count(distinct product_id)        as qtd_produtos_distintos,
    count(distinct seller_id)         as qtd_vendedores_distintos,
    sum(price)                        as valor_itens,
    sum(freight_value)                as valor_frete
from itens
where order_id is not null
group by order_id
