-- Features do modelo de previsao de atraso (Etapa 4), uma linha por pedido.
--
-- Regra que governa este model: so entra o que ja existe NO ATO DA COMPRA.
-- A lista permitida e repetida em ml/features.py (PERMITIDAS), e um teste
-- Python falha se o modelo receber qualquer coluna fora dela.
--
-- Ficaram de fora, de proposito (detalhe em docs/modelo-atraso.md):
--   approved_at                        posterior a compra (boleto leva dias)
--   delivered_carrier_at, dias_ate_transportadora   posterior a compra
--   delivered_customer_at, tempo_entrega_dias, dias_em_transporte   e o desfecho
--   atraso_dias, entregue_no_prazo     e o alvo
--   nota_avaliacao                     avaliacao vem depois da entrega
--   order_status, status_pedido, situacao_pedido   mudam ao longo do pedido
--   valor_pago, qtd_pagamentos         redundantes com valor e parcelas
--   ano_compra                         o ano nao se repete no futuro
--
-- Colunas de controle (nao sao features): pedido_sk, order_id, purchased_at
-- (separacao temporal) e atrasou (alvo; nulo quando ainda nao houve entrega).
with pedidos as (
    select * from {{ ref('fato_pedidos') }}
    where purchased_at >= '2017-01-01'
      and purchased_at <  '2018-09-01'
      and order_status not in ('canceled', 'unavailable')
),

orders as (
    select order_id, customer_id from {{ ref('stg_olist__orders') }}
),

customers as (
    select customer_id, zip_code_prefix, state from {{ ref('stg_olist__customers') }}
),

itens as (
    select
        i.order_id,
        i.order_item_id,
        i.valor_item,
        v.zip_code_prefix as vendedor_cep,
        v.uf              as vendedor_uf,
        v.regiao          as vendedor_regiao,
        p.categoria_grupo,
        p.peso_g,
        p.volume_cm3
    from {{ ref('fato_itens_pedido') }} i
    left join {{ ref('dim_vendedores') }} v on i.vendedor_sk = v.vendedor_sk
    left join {{ ref('dim_produtos') }}   p on i.produto_sk = p.produto_sk
),

-- Vendedor e categoria "principais": os do item de maior valor do pedido.
-- 98% dos pedidos tem um vendedor so; para o resto, o item mais caro decide.
item_principal as (
    select *
    from (
        select
            itens.*,
            row_number() over (
                partition by order_id
                order by valor_item desc, order_item_id
            ) as rn
        from itens
    ) t
    where rn = 1
),

carga as (
    select
        order_id,
        sum(peso_g)     as peso_total_g,
        sum(volume_cm3) as volume_total_cm3
    from itens
    group by order_id
),

-- Forma de pagamento de maior valor, escolhida no checkout.
pagamento_principal as (
    select order_id, payment_type
    from (
        select
            order_id,
            payment_type,
            row_number() over (
                partition by order_id
                order by payment_value desc, payment_sequential
            ) as rn
        from {{ ref('stg_olist__order_payments') }}
    ) t
    where rn = 1
),

-- 11 prefixos de CEP da origem tem coordenada media fora do Brasil (um CEP do
-- PR cai na Espanha). Ponto fora da caixa do pais e descartado aqui, e a
-- distancia desse pedido fica nula, como a de CEP sem coordenada. A dimensao
-- nao e alterada: o mapa do dashboard agrega por UF e nao sofre com isso.
geo as (
    select zip_code_prefix, latitude::float8 as lat, longitude::float8 as lng
    from {{ ref('dim_geolocalizacao') }}
    where latitude between -33.8 and 5.3
      and longitude between -74.0 and -34.7
),

base as (
    select
        p.pedido_sk,
        p.order_id,
        p.purchased_at,
        case
            when p.entregue_no_prazo is null then null
            when p.entregue_no_prazo then 0
            else 1
        end as atrasou,

        (p.estimated_delivery_at::date - p.purchased_at::date) as prazo_prometido_dias,

        c.state                       as cliente_uf,
        {{ regiao_br('c.state') }}    as cliente_regiao,
        ip.vendedor_uf,
        ip.vendedor_regiao,

        p.valor_itens,
        p.valor_frete,
        p.valor_frete / nullif(p.valor_itens, 0) as frete_sobre_valor,
        p.qtd_itens,
        p.qtd_vendedores_distintos,
        p.qtd_produtos_distintos,
        cg.peso_total_g,
        cg.volume_total_cm3,
        ip.categoria_grupo,
        pg.payment_type as tipo_pagamento,
        p.max_parcelas,

        extract(month  from p.purchased_at)::int as mes_compra,
        extract(isodow from p.purchased_at)::int as dia_semana_compra,
        extract(hour   from p.purchased_at)::int as hora_compra,

        -- Termo interno do haversine (raiz do "h"); nulo se faltar um CEP.
        sqrt(
            power(sin(radians(gv.lat - gc.lat) / 2), 2)
            + cos(radians(gc.lat)) * cos(radians(gv.lat))
              * power(sin(radians(gv.lng - gc.lng) / 2), 2)
        ) as h
    from pedidos p
    left join orders o               on p.order_id = o.order_id
    left join customers c            on o.customer_id = c.customer_id
    left join item_principal ip      on p.order_id = ip.order_id
    left join carga cg               on p.order_id = cg.order_id
    left join pagamento_principal pg on p.order_id = pg.order_id
    left join geo gc                 on c.zip_code_prefix = gc.zip_code_prefix
    left join geo gv                 on ip.vendedor_cep = gv.zip_code_prefix
)

select
    pedido_sk,
    order_id,
    purchased_at,
    atrasou,
    prazo_prometido_dias,
    cliente_uf,
    cliente_regiao,
    vendedor_uf,
    vendedor_regiao,
    case
        when cliente_regiao is null or vendedor_regiao is null then null
        when cliente_regiao <> vendedor_regiao then 'sim'
        else 'nao'
    end as venda_interregional,
    -- Haversine, raio da Terra 6371 km. Nulo quando um dos CEPs nao esta na
    -- base de geolocalizacao (o modelo principal trata nulo nativamente).
    -- O case protege o asin de arredondamento acima de 1. Nao usar least():
    -- no Postgres, least(1, null) devolve 1, e CEP sem coordenada viraria
    -- 20 mil km em vez de nulo (o teste assert_distancia_km_plausivel pega).
    2 * 6371 * asin(case when h > 1 then 1 else h end) as distancia_km,
    valor_itens,
    valor_frete,
    frete_sobre_valor,
    qtd_itens,
    qtd_vendedores_distintos,
    qtd_produtos_distintos,
    peso_total_g,
    volume_total_cm3,
    categoria_grupo,
    tipo_pagamento,
    max_parcelas,
    mes_compra,
    dia_semana_compra,
    hora_compra
from base
