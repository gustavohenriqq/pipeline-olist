-- Fato no grao de PEDIDO (uma linha por pedido).
-- Traz as chaves para as dimensoes (cliente, tempo, geolocalizacao) e as
-- metricas aditivas do pedido (valores, pagamento, nota, tempo de entrega).
--
-- Nota de modelagem: produto e vendedor nao entram aqui porque um pedido pode
-- ter varios produtos/vendedores (grao diferente). Essa ligacao esta em
-- fato_itens_pedido, no grao de item. Ter os dois fatos e o padrao correto de
-- star schema quando existem graos diferentes.
with orders as (
    select * from {{ ref('stg_olist__orders') }}
),

customers as (
    select * from {{ ref('stg_olist__customers') }}
),

pagamentos as (
    select * from {{ ref('int_pagamentos_por_pedido') }}
),

itens as (
    select * from {{ ref('int_itens_por_pedido') }}
),

avaliacao as (
    select * from {{ ref('int_avaliacao_por_pedido') }}
)

select
    {{ gera_sk(['o.order_id']) }} as pedido_sk,
    o.order_id,

    -- Chaves para as dimensoes
    {{ gera_sk(['c.customer_unique_id']) }} as cliente_sk,
    {{ gera_sk(['c.zip_code_prefix']) }}    as geo_sk,
    cast(to_char(o.purchased_at, 'YYYYMMDD') as integer)            as tempo_sk_compra,

    -- Dimensoes degeneradas (ficam no proprio fato)
    o.order_status,
    p.tipos_pagamento,

    -- Metricas de valor
    coalesce(i.qtd_itens, 0)                          as qtd_itens,
    coalesce(i.qtd_produtos_distintos, 0)             as qtd_produtos_distintos,
    coalesce(i.qtd_vendedores_distintos, 0)           as qtd_vendedores_distintos,
    coalesce(i.valor_itens, 0)                        as valor_itens,
    coalesce(i.valor_frete, 0)                        as valor_frete,
    coalesce(i.valor_itens, 0) + coalesce(i.valor_frete, 0) as valor_total,
    p.valor_pago,
    p.qtd_pagamentos,
    p.max_parcelas,

    -- Metrica de satisfacao
    a.review_score                                    as nota_avaliacao,

    -- Carimbos de tempo (uteis para o BI recalcular se precisar)
    o.purchased_at,
    o.approved_at,
    o.delivered_carrier_at,
    o.delivered_customer_at,
    o.estimated_delivery_at,

    -- Metricas de logistica (em dias)
    (o.delivered_customer_at::date - o.purchased_at::date)      as tempo_entrega_dias,
    (o.delivered_customer_at::date - o.estimated_delivery_at::date) as atraso_dias,

    -- Decomposicao do tempo de entrega em duas responsabilidades.
    -- Existe porque a pergunta "de quem e o atraso?" nao tem resposta olhando
    -- so o tempo total: vendedor que demora a despachar e transportadora lenta
    -- produzem o mesmo numero no fim, mas exigem acoes opostas (SLA de
    -- despacho contra malha logistica).
    --
    -- Foi a analise que pediu estes campos, nao o contrario. Ver
    -- docs/analise-atraso.md, secao "de quem e o atraso".
    (o.delivered_carrier_at::date  - o.purchased_at::date)      as dias_ate_transportadora,
    (o.delivered_customer_at::date - o.delivered_carrier_at::date) as dias_em_transporte,

    -- Flags
    (o.order_status = 'delivered')                    as foi_entregue,
    case
        when o.delivered_customer_at is null then null
        when o.delivered_customer_at::date <= o.estimated_delivery_at::date then true
        else false
    end                                               as entregue_no_prazo
from orders o
left join customers c   on o.customer_id = c.customer_id
left join pagamentos p  on o.order_id = p.order_id
left join itens i       on o.order_id = i.order_id
left join avaliacao a   on o.order_id = a.order_id
