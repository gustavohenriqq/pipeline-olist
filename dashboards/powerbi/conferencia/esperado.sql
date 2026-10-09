-- Valores esperados do modelo Power BI, calculados direto nas marts.
-- Uma linha por caso: caso | valor. O conferir.ps1 compara com o DAX de casos.json.
-- "vazio" significa que a medida deve sair em branco.
with entregas as (
    select
        f.order_id,
        c.uf,
        c.regiao,
        f.entregue_no_prazo
    from marts.fato_pedidos f
    join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
),
nacional as (
    select avg(case when not entregue_no_prazo then 1.0 else 0.0 end) as taxa
    from entregas
    where entregue_no_prazo is not null
),
receita_mes as (
    select to_char(purchased_at, 'YYYY-MM') as mes, sum(valor_total) as receita
    from marts.fato_pedidos
    group by 1
),
honestas as (
    select p.pedido_sk, f.valor_total
    from marts.previsao_atraso p
    join marts.fato_pedidos f on f.pedido_sk = p.pedido_sk
    where p.alerta and p.conjunto in ('teste', 'em_andamento')
),
usuarios as (
    select distinct email, perfil from marts.seguranca_bi
),
visiveis as (
    -- Pedidos e itens que cada usuario do seed deve enxergar.
    select u.email, f.order_id, null::text as item_sk
    from usuarios u
    join marts.fato_pedidos f on u.perfil = 'Diretoria'
    union all
    select s.email, f.order_id, null
    from marts.seguranca_bi s
    join marts.dim_clientes c on c.regiao = s.regiao
    join marts.fato_pedidos f on f.cliente_sk = c.cliente_sk
    where s.perfil = 'Gerente regional'
    union all
    select distinct s.email, i.order_id, null
    from marts.seguranca_bi s
    join marts.dim_vendedores v on v.seller_id = s.seller_id
    join marts.fato_itens_pedido i on i.vendedor_sk = v.vendedor_sk
    where s.perfil = 'Vendedor'
),
itens_visiveis as (
    select u.email, i.item_sk
    from usuarios u
    join marts.fato_itens_pedido i on u.perfil = 'Diretoria'
    union all
    select s.email, i.item_sk
    from marts.seguranca_bi s
    join marts.dim_clientes c on c.regiao = s.regiao
    join marts.fato_itens_pedido i on i.cliente_sk = c.cliente_sk
    where s.perfil = 'Gerente regional'
    union all
    select s.email, i.item_sk
    from marts.seguranca_bi s
    join marts.dim_vendedores v on v.seller_id = s.seller_id
    join marts.fato_itens_pedido i on i.vendedor_sk = v.vendedor_sk
    where s.perfil = 'Vendedor'
)
select 'linhas_fato_pedidos', count(*)::text from marts.fato_pedidos
union all select 'linhas_fato_itens_pedido', count(*)::text from marts.fato_itens_pedido
union all select 'linhas_dim_clientes', count(*)::text from marts.dim_clientes
union all select 'linhas_dim_produtos', count(*)::text from marts.dim_produtos
union all select 'linhas_dim_vendedores', count(*)::text from marts.dim_vendedores
union all select 'linhas_dim_tempo', count(*)::text from marts.dim_tempo
union all select 'linhas_previsao_atraso', count(*)::text from marts.previsao_atraso
union all select 'linhas_seguranca_bi', count(*)::text from marts.seguranca_bi
union all select 'pedidos', count(distinct order_id)::text from marts.fato_pedidos
union all select 'receita', sum(valor_total)::text from marts.fato_pedidos
-- Moeda no Power BI e decimal fixo de 4 casas: moeda / inteiro sai arredondado ali.
union all select 'ticket_medio', round(sum(valor_total) / count(distinct order_id), 4)::text from marts.fato_pedidos
union all select 'pct_no_prazo',
    avg(case when entregue_no_prazo then 1.0 else 0.0 end)::text
    from marts.fato_pedidos where entregue_no_prazo is not null
union all select 'nota_media', avg(nota_avaliacao)::text from marts.fato_pedidos
union all select 'excesso_rj',
    (sum(case when not e.entregue_no_prazo then 1 else 0 end) - count(*) * max(n.taxa))::text
    from entregas e cross join nacional n
    where e.uf = 'RJ' and e.entregue_no_prazo is not null
-- Acumulado no ano em marco: jan a mar/2018. No ano cheio o TOTALYTD seria igual
-- a receita do ano e o caso nao testaria nada.
union all select 'receita_acumulada_2018_03', sum(valor_total)::text
    from marts.fato_pedidos where purchased_at >= '2018-01-01' and purchased_at < '2018-04-01'
union all select 'variacao_mensal_2018_03',
    ((select receita from receita_mes where mes = '2018-03')
      / (select receita from receita_mes where mes = '2018-02') - 1)::text
union all select 'variacao_mensal_2016_09', 'vazio'
union all select 'pedidos_alerta', count(*)::text from honestas
union all select 'receita_risco', sum(valor_total)::text from honestas
union all select 'pedidos@' || email, count(distinct order_id)::text from visiveis group by email
union all select 'itens@' || email, count(distinct item_sk)::text from itens_visiveis group by email
union all select 'pedidos@fora@exemplo.com.br', '0'
union all select 'itens@fora@exemplo.com.br', '0';
