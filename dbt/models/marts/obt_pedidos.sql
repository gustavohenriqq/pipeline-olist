-- OBT (One Big Table) de pedidos: o star schema achatado numa tabela unica,
-- no mesmo grao de fato_pedidos (uma linha por pedido).
--
-- Por que existe, se o star schema ja esta pronto?
--   Ferramentas de BI conectadas via SQL direto (Looker Studio, por exemplo)
--   tratam cada tabela como uma fonte separada e so juntam por "blend", que e
--   limitado (poucas fontes, sem join a esquerda completo, agregacao antes do
--   join). Uma tabela larga elimina esse atrito: o analista arrasta campo e o
--   grafico sai certo.
--
-- Por que NAO substituir o star schema por isso?
--   O star continua sendo a verdade: e ele que tem os testes de integridade
--   referencial e e nele que o Power BI (Fase 4) e o agente de IA (Fase 6) vao
--   ligar, porque o motor VertiPaq e o texto-para-SQL trabalham melhor com
--   modelo dimensional. A OBT e conveniencia de servico, derivada, descartavel.
--
-- Grao: um pedido. Nao inclui produto nem vendedor, que vivem no grao de item
-- (fato_itens_pedido). Achatar os dois graus numa tabela so multiplicaria as
-- metricas de pedido e produziria receita inflada.
with pedidos as (
    select * from {{ ref('fato_pedidos') }}
),

clientes as (
    select * from {{ ref('dim_clientes') }}
),

tempo as (
    select * from {{ ref('dim_tempo') }}
),

geo as (
    select * from {{ ref('dim_geolocalizacao') }}
)

select
    p.pedido_sk,
    p.order_id,
    p.order_status,

    -- Cliente (grao de pessoa, nao de pedido)
    c.customer_unique_id,
    c.cidade                     as cliente_cidade,
    c.uf                         as cliente_uf,
    c.regiao                     as cliente_regiao,

    -- Coordenadas do CEP do cliente, para o mapa do Looker.
    -- LEFT JOIN de proposito: 278 pedidos tem CEP fora da base de
    -- geolocalizacao do Olist. Perder esses pedidos do dashboard so para
    -- preencher um mapa seria trocar receita real por estetica.
    g.latitude                   as cliente_latitude,
    g.longitude                  as cliente_longitude,

    -- Campo pronto para o mapa do Looker Studio, que espera "lat,long".
    case
        when g.latitude is not null and g.longitude is not null
            then g.latitude || ',' || g.longitude
    end                          as cliente_latlong,

    -- Tempo da compra, ja desmembrado para nao depender de funcao de data no BI
    t.data                       as data_compra,
    t.ano                        as ano_compra,
    t.mes                        as mes_compra,
    t.ano_mes                    as ano_mes_compra,
    t.trimestre                  as trimestre_compra,
    t.nome_mes                   as nome_mes_compra,
    t.nome_dia_semana            as dia_semana_compra,
    t.fim_de_semana              as compra_no_fim_de_semana,

    -- Metricas do pedido
    p.qtd_itens,
    p.qtd_produtos_distintos,
    p.qtd_vendedores_distintos,
    p.valor_itens,
    p.valor_frete,
    p.valor_total,
    p.valor_pago,
    p.qtd_pagamentos,
    p.max_parcelas,
    p.tipos_pagamento,

    -- Satisfacao e entrega
    p.nota_avaliacao,
    p.purchased_at,
    p.delivered_carrier_at,
    p.delivered_customer_at,
    p.estimated_delivery_at,
    p.tempo_entrega_dias,
    p.atraso_dias,

    -- Decomposicao do tempo: quanto foi do vendedor, quanto foi do transporte.
    -- 87% do atraso nasce no transporte. Ver docs/analise-atraso.md.
    p.dias_ate_transportadora,
    p.dias_em_transporte,

    p.foi_entregue,
    p.entregue_no_prazo

from pedidos p
left join clientes c on c.cliente_sk = p.cliente_sk
left join tempo    t on t.tempo_sk   = p.tempo_sk_compra
left join geo      g on g.geo_sk     = p.geo_sk
