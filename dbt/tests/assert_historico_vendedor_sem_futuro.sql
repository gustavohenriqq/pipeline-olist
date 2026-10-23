-- O historico do vendedor so pode usar pedido comprado E entregue antes do dia
-- da compra (issue 18). Este teste falha se ml_historico_vendedor contar
-- qualquer pedido posterior, de tres jeitos independentes:
--
--   1. a ultima entrega usada nao e anterior ao dia da compra;
--   2. a contagem por vendedor difere da recontagem por juncao direta, com a
--      regra escrita por extenso (entrega < compra_dia e compra < compra_dia);
--   3. o mesmo para a taxa geral da plataforma.
--
-- A recontagem nao usa a soma acumulada do model. Prova (23/10/2026, base
-- completa): com a ordem dos eventos invertida no model, de modo que a entrega
-- do proprio dia da compra passasse a contar, este teste devolveu 77.214
-- linhas (38.607 pares com a contagem errada, os mesmos com a ultima entrega
-- no dia da compra). Tirar o greatest do model nao muda nada hoje: a base nao
-- tem pedido entregue antes da propria compra.
with pedidos as (
    select
        order_id,
        purchased_at::date          as compra_dia,
        delivered_customer_at::date as entrega_dia,
        case when entregue_no_prazo then 0 else 1 end as atrasou
    from {{ ref('fato_pedidos') }}
    where entregue_no_prazo is not null
),

pares as (
    select distinct i.order_id, i.vendedor_sk, p.purchased_at::date as compra_dia
    from {{ ref('fato_itens_pedido') }} i
    join {{ ref('fato_pedidos') }} p on p.order_id = i.order_id
),

entregas_vendedor as (
    select distinct i.vendedor_sk, d.order_id, d.compra_dia, d.entrega_dia, d.atrasou
    from {{ ref('fato_itens_pedido') }} i
    join pedidos d on d.order_id = i.order_id
),

esperado_vendedor as (
    select
        a.order_id,
        a.vendedor_sk,
        count(e.order_id)            as hist_entregues,
        coalesce(sum(e.atrasou), 0)  as hist_atrasos
    from pares a
    left join entregas_vendedor e
        on  e.vendedor_sk = a.vendedor_sk
        and e.entrega_dia < a.compra_dia
        and e.compra_dia  < a.compra_dia
    group by a.order_id, a.vendedor_sk
),

dias as (
    select distinct compra_dia from pares
),

esperado_geral as (
    select
        d.compra_dia,
        count(p.order_id)           as geral_entregues,
        coalesce(sum(p.atrasou), 0) as geral_atrasos
    from dias d
    left join pedidos p
        on  p.entrega_dia < d.compra_dia
        and p.compra_dia  < d.compra_dia
    group by d.compra_dia
),

modelo as (
    select * from {{ ref('ml_historico_vendedor') }}
)

select 'ultima entrega no dia da compra ou depois' as falha, m.order_id, m.vendedor_sk
from modelo m
where m.hist_ultima_entrega >= m.compra_dia

union all

select 'contagem do vendedor diverge', coalesce(m.order_id, e.order_id), coalesce(m.vendedor_sk, e.vendedor_sk)
from esperado_vendedor e
full join modelo m on m.order_id = e.order_id and m.vendedor_sk = e.vendedor_sk
where m.hist_entregues is distinct from e.hist_entregues
   or m.hist_atrasos   is distinct from e.hist_atrasos

union all

select 'taxa geral diverge', m.order_id, m.vendedor_sk
from modelo m
join esperado_geral g on g.compra_dia = m.compra_dia
where m.geral_entregues is distinct from g.geral_entregues
   or m.geral_atrasos   is distinct from g.geral_atrasos
