-- Valores esperados dos visuais do painel web que nao tem caso no esperado.sql do
-- Power BI. Escritos a mao, sem reaproveitar o SQL de painel/consultas.py, na base
-- inteira. Uma linha por caso: caso | valor (texto).
with entregues as (
    select f.order_id, c.uf, c.regiao, f.entregue_no_prazo
    from marts.fato_pedidos f
    join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
    where f.entregue_no_prazo is not null
),
nacional as (
    select sum(case when not entregue_no_prazo then 1 else 0 end)::numeric / count(*) as taxa
    from entregues
),
excesso as (
    select e.uf, sum(case when not e.entregue_no_prazo then 1 else 0 end) - count(*) * max(n.taxa) as valor
    from entregues e cross join nacional n
    group by e.uf
),
grupos as (
    select p.categoria_grupo, sum(i.valor_item) as receita
    from marts.fato_itens_pedido i
    join marts.dim_produtos p on p.produto_sk = i.produto_sk
    group by 1
),
vendedores as (
    select v.vendedor_rotulo, sum(i.valor_item) as receita
    from marts.fato_itens_pedido i
    join marts.dim_vendedores v on v.vendedor_sk = i.vendedor_sk
    group by 1
),
pedidos_dos_itens as (
    select distinct order_id from marts.fato_itens_pedido
)
select 'taxa_nacional', (select taxa from nacional)::text
union all select 'taxa_regiao_nordeste',
    (sum(case when not entregue_no_prazo then 1 else 0 end)::numeric / count(*))::text
    from entregues where regiao = 'Nordeste'
union all select 'primeira_uf_excesso', (select uf from excesso order by valor desc, uf limit 1)
union all select 'itens', count(*)::text from marts.fato_itens_pedido
union all select 'receita_itens', sum(valor_item)::text from marts.fato_itens_pedido
union all select 'taxa_atraso_itens',
    (sum(case when not f.entregue_no_prazo then 1 else 0 end)::numeric / count(*))::text
    from marts.fato_pedidos f
    where f.entregue_no_prazo is not null
      and f.order_id in (select order_id from pedidos_dos_itens)
union all select 'primeiro_grupo', (select categoria_grupo from grupos order by receita desc, categoria_grupo limit 1)
union all select 'receita_primeiro_grupo', (select max(receita) from grupos)::text
union all select 'primeiro_vendedor', (select vendedor_rotulo from vendedores order by receita desc, vendedor_rotulo limit 1)
union all select 'pedidos_em_risco_linhas',
    least(50, count(*))::text from marts.previsao_atraso where conjunto = 'em_andamento';
