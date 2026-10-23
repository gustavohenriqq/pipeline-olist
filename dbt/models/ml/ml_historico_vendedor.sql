-- Historico de entrega de cada vendedor COMO ERA NA DATA DA COMPRA, uma linha
-- por par (pedido, vendedor). Alimenta a taxa de atraso do vendedor em
-- ml_features_atraso (issue 18).
--
-- Regra: um pedido do historico so conta se o desfecho dele ja era conhecido
-- no dia anterior a compra, ou seja, se foi comprado E entregue antes do dia
-- da compra. "conhecido_em" = maior das duas datas; o greatest protege contra
-- pedido com entrega anterior a propria compra (datas impossiveis da origem).
-- Entrega no proprio dia da compra fica de fora: o modelo roda no ato da
-- compra e nao sabe a hora em que a entrega foi registrada.
--
-- Pedido ainda em transito na data da compra nao conta, nem se ja estiver
-- vencido: so pedido entregue tem desfecho fechado. Isso puxa a taxa um pouco
-- para baixo (os atrasados demoram mais a entrar), mas e o que existiria em
-- producao naquele dia.
--
-- Como e calculado sem juntar cada pedido com todo o historico do vendedor:
-- compras (tipo 0) e entregas (tipo 1) viram eventos numa fila por dia. A soma
-- acumulada ate a linha da compra pega as entregas de dias anteriores; as do
-- mesmo dia vem depois na ordem (tipo 1 > tipo 0) e ficam de fora.
-- O teste assert_historico_vendedor_sem_futuro recalcula tudo pela regra
-- escrita acima, por juncao direta, e falha se algum numero divergir ou se a
-- ultima entrega usada nao for anterior ao dia da compra.
with pedidos as (
    select
        order_id,
        purchased_at::date as compra_dia,
        greatest(delivered_customer_at, purchased_at)::date as conhecido_em,
        case
            when entregue_no_prazo is null then null
            when entregue_no_prazo then 0
            else 1
        end as atrasou
    from {{ ref('fato_pedidos') }}
),

pares as (
    select distinct i.order_id, i.vendedor_sk, p.compra_dia, p.conhecido_em, p.atrasou
    from {{ ref('fato_itens_pedido') }} i
    join pedidos p on p.order_id = i.order_id
),

eventos_vendedor as (
    select vendedor_sk, compra_dia as dia, 0 as tipo, order_id,
           0 as entregue, 0 as atrasou, null::date as entrega
    from pares
    union all
    select vendedor_sk, conhecido_em, 1, null,
           1, atrasou, conhecido_em
    from pares
    where atrasou is not null
),

acumulado_vendedor as (
    select
        order_id,
        vendedor_sk,
        dia as compra_dia,
        sum(entregue) over w as hist_entregues,
        sum(atrasou)  over w as hist_atrasos,
        max(entrega)  over w as hist_ultima_entrega
    from eventos_vendedor
    window w as (
        partition by vendedor_sk
        order by dia, tipo
        rows between unbounded preceding and current row
    )
),

-- Mesma fila para a plataforma inteira, no grao de pedido: a taxa geral da
-- data da compra serve de ponto de partida para vendedor com pouco historico.
eventos_geral as (
    select compra_dia as dia, 0 as tipo, 0 as entregue, 0 as atrasou from pedidos
    union all
    select conhecido_em, 1, 1, atrasou from pedidos where atrasou is not null
),

acumulado_geral as (
    select distinct on (dia)
        dia as compra_dia,
        sum(entregue) over w as geral_entregues,
        sum(atrasou)  over w as geral_atrasos
    from eventos_geral
    window w as (order by dia, tipo rows between unbounded preceding and current row)
    -- a linha de compra mais adiantada do dia: todas tem o mesmo acumulado,
    -- porque nenhuma entrega do dia entra antes delas
    order by dia, tipo
)

select
    v.order_id,
    v.vendedor_sk,
    v.compra_dia,
    v.hist_entregues::int     as hist_entregues,
    v.hist_atrasos::int       as hist_atrasos,
    v.hist_ultima_entrega,
    g.geral_entregues::int    as geral_entregues,
    g.geral_atrasos::int      as geral_atrasos
from acumulado_vendedor v
join acumulado_geral g on g.compra_dia = v.compra_dia
where v.order_id is not null
