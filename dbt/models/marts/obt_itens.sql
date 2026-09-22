-- OBT (One Big Table) de itens: o star schema achatado no grao de ITEM,
-- uma linha por item de pedido.
--
-- Complementa obt_pedidos. Sao dois graos diferentes e por isso duas tabelas:
--   obt_pedidos -> receita, ticket medio, entrega, satisfacao (metrica do pedido)
--   obt_itens   -> categoria de produto e performance de vendedor
--
-- Juntar as duas numa so multiplicaria as metricas de pedido pelo numero de
-- itens e produziria receita inflada. Esse e o erro classico de quem achata um
-- star schema sem olhar o grao. As metricas daqui (valor_produto, valor_frete,
-- valor_item) sao aditivas no grao de item e podem ser somadas a vontade.
with itens as (
    select * from {{ ref('fato_itens_pedido') }}
),

produtos as (
    select * from {{ ref('dim_produtos') }}
),

vendedores as (
    select * from {{ ref('dim_vendedores') }}
),

clientes as (
    select * from {{ ref('dim_clientes') }}
),

tempo as (
    select * from {{ ref('dim_tempo') }}
)

select
    i.item_sk,
    i.order_id,
    i.order_item_id,

    -- Produto
    pr.product_id,
    pr.categoria_pt,
    pr.categoria_nome,
    pr.categoria_grupo,
    -- coalesce porque nem toda categoria do Olist tem traducao oficial.
    -- Sem isso, o grafico em ingles perderia linhas em vez de mostrar o nome PT.
    coalesce(pr.categoria_en, pr.categoria_pt) as categoria_en,
    pr.peso_g,
    pr.volume_cm3,
    pr.qtd_fotos,

    -- Vendedor
    v.seller_id,
    v.cidade                     as vendedor_cidade,
    v.uf                         as vendedor_uf,
    v.regiao                     as vendedor_regiao,

    -- Cliente (para cruzar origem e destino da venda)
    c.cidade                     as cliente_cidade,
    c.uf                         as cliente_uf,
    c.regiao                     as cliente_regiao,

    -- Marca venda entre regioes diferentes, que costuma explicar frete alto
    -- e prazo maior. E uma pergunta de negocio que o dashboard responde bem.
    case
        when v.regiao is null or c.regiao is null then null
        when v.regiao = c.regiao then false
        else true
    end                          as venda_interregional,

    -- Tempo da compra
    t.data                       as data_compra,
    t.ano                        as ano_compra,
    t.mes                        as mes_compra,
    t.ano_mes                    as ano_mes_compra,
    t.trimestre                  as trimestre_compra,
    t.nome_mes                   as nome_mes_compra,

    -- Metricas aditivas no grao de item
    i.valor_produto,
    i.valor_frete,
    i.valor_item

from itens i
left join produtos   pr on pr.produto_sk  = i.produto_sk
left join vendedores v  on v.vendedor_sk  = i.vendedor_sk
left join clientes   c  on c.cliente_sk   = i.cliente_sk
left join tempo      t  on t.tempo_sk     = i.tempo_sk_compra
