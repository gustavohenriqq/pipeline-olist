-- Fato no grao de ITEM do pedido (uma linha por item).
-- E aqui que produto e vendedor se conectam ao modelo, pois cada item tem
-- exatamente um produto e um vendedor. Complementa o fato_pedidos.
with itens as (
    select * from {{ ref('stg_olist__order_items') }}
),

orders as (
    select * from {{ ref('stg_olist__orders') }}
),

customers as (
    select * from {{ ref('stg_olist__customers') }}
)

select
    {{ gera_sk(['i.order_id', 'i.order_item_id']) }} as item_sk,
    i.order_id,
    i.order_item_id,

    -- Chaves para as dimensoes
    {{ gera_sk(['i.product_id']) }}          as produto_sk,
    {{ gera_sk(['i.seller_id']) }}           as vendedor_sk,
    {{ gera_sk(['c.customer_unique_id']) }}  as cliente_sk,
    cast(to_char(o.purchased_at, 'YYYYMMDD') as integer)             as tempo_sk_compra,

    -- Metricas
    i.price          as valor_produto,
    i.freight_value  as valor_frete,
    (i.price + i.freight_value) as valor_item
from itens i
left join orders o     on i.order_id = o.order_id
left join customers c  on o.customer_id = c.customer_id
