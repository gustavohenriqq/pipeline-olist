"""Consultas do painel: uma funcao por visual, (conexao, filtros) -> DataFrame.

As definicoes repetem as medidas DAX do Power BI (Etapa 5) e sao conferidas contra
dashboards/powerbi/conferencia/esperado.sql nos testes de integracao. Filtro vai
sempre como parametro nomeado, nunca no texto do SQL.
"""
from __future__ import annotations

from dataclasses import replace

import pandas as pd

from agente.banco import executar
from painel.filtros import Filtros, mes_anterior, mes_referencia

# Pedidos do periodo, com a regiao do cliente opcional. Base de quase tudo no painel.
_PEDIDOS = """
    select f.order_id, f.valor_total, f.entregue_no_prazo, f.nota_avaliacao,
           to_char(f.purchased_at, 'YYYY-MM') as mes
    from marts.fato_pedidos f
    left join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
    where f.purchased_at::date between %(inicio)s and %(fim)s
      and (%(regiao)s::text is null or c.regiao = %(regiao)s)
"""
# Receita por mes sem o corte de datas (para mes anterior e ano anterior).
_RECEITA_POR_MES = """
    select to_char(f.purchased_at, 'YYYY-MM') as mes, sum(f.valor_total) as receita
    from marts.fato_pedidos f
    left join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
    where (%(regiao)s::text is null or c.regiao = %(regiao)s)
    group by 1
"""
_PCT_NO_PRAZO = "avg(case when entregue_no_prazo then 1.0 else 0.0 end) filter (where entregue_no_prazo is not null)"


def _parametros(f: Filtros) -> dict:
    ref = mes_referencia(f)
    return {"inicio": f.inicio, "fim": f.fim, "regiao": f.regiao, "ref": ref, "ant": mes_anterior(ref)}


def _consulta(conexao, sql: str, f: Filtros) -> pd.DataFrame:
    colunas, linhas = executar(conexao, sql, _parametros(f))
    df = pd.DataFrame(linhas, columns=colunas)
    # Decimal do psycopg2 vira float: as contas e os graficos esperam numero.
    for coluna in df.columns:
        if df[coluna].map(lambda v: v.__class__.__name__ == "Decimal").any():
            df[coluna] = df[coluna].astype(float)
    return df


def delta(ref, ant, *, taxa: bool) -> float | None:
    """Destaque do cartao: valor em fracao (ref/ant - 1); taxa em pontos percentuais."""
    if ref is None or ant is None or pd.isna(ref) or pd.isna(ant):
        return None
    if taxa:
        return (float(ref) - float(ant)) * 100
    if float(ant) == 0:
        return None
    return float(ref) / float(ant) - 1


def cartoes_executivo(conexao, f: Filtros) -> pd.DataFrame:
    sql = f"""
    with base as ({_PEDIDOS})
    select
        sum(valor_total) as receita,
        count(distinct order_id) as pedidos,
        sum(valor_total) / nullif(count(distinct order_id), 0) as ticket_medio,
        {_PCT_NO_PRAZO} as pct_no_prazo,
        avg(nota_avaliacao) as nota_media,
        sum(valor_total) filter (where mes = %(ref)s) as receita_ref,
        sum(valor_total) filter (where mes = %(ant)s) as receita_ant,
        count(distinct order_id) filter (where mes = %(ref)s) as pedidos_ref,
        count(distinct order_id) filter (where mes = %(ant)s) as pedidos_ant,
        sum(valor_total) filter (where mes = %(ref)s)
            / nullif(count(distinct order_id) filter (where mes = %(ref)s), 0) as ticket_ref,
        sum(valor_total) filter (where mes = %(ant)s)
            / nullif(count(distinct order_id) filter (where mes = %(ant)s), 0) as ticket_ant,
        avg(case when entregue_no_prazo then 1.0 else 0.0 end)
            filter (where entregue_no_prazo is not null and mes = %(ref)s) as pct_ref,
        avg(case when entregue_no_prazo then 1.0 else 0.0 end)
            filter (where entregue_no_prazo is not null and mes = %(ant)s) as pct_ant,
        avg(nota_avaliacao) filter (where mes = %(ref)s) as nota_ref,
        avg(nota_avaliacao) filter (where mes = %(ant)s) as nota_ant
    from base
    having count(*) > 0
    """
    return _consulta(conexao, sql, f)


def receita_mensal(conexao, f: Filtros) -> pd.DataFrame:
    sql = f"""
    with periodo as (
        select mes as ano_mes, sum(valor_total) as receita from ({_PEDIDOS}) p group by 1
    ),
    todos as ({_RECEITA_POR_MES})
    select p.ano_mes, p.receita, a.receita as receita_ano_anterior
    from periodo p
    left join todos a
      on a.mes = to_char(to_date(p.ano_mes, 'YYYY-MM') - interval '1 year', 'YYYY-MM')
    order by p.ano_mes
    """
    return _consulta(conexao, sql, f)


def placar_mensal(conexao, f: Filtros) -> pd.DataFrame:
    sql = f"""
    with periodo as (
        select mes as ano_mes, sum(valor_total) as receita, count(distinct order_id) as pedidos,
               sum(valor_total) / nullif(count(distinct order_id), 0) as ticket_medio,
               {_PCT_NO_PRAZO} as pct_no_prazo
        from ({_PEDIDOS}) p
        group by 1
    ),
    todos as ({_RECEITA_POR_MES})
    select p.ano_mes, p.receita,
           p.receita / nullif(a.receita, 0) - 1 as variacao_mensal,
           p.pedidos, p.ticket_medio, p.pct_no_prazo
    from periodo p
    left join todos a
      on a.mes = to_char(to_date(p.ano_mes, 'YYYY-MM') - interval '1 month', 'YYYY-MM')
    order by p.ano_mes desc
    """
    return _consulta(conexao, sql, f)


# ---- Entrega e risco e Vendedores: sem filtro de regiao, como no Power BI ----

def _sem_regiao(f: Filtros) -> Filtros:
    return replace(f, regiao=None)


_ENTREGUES = """
    select c.uf, c.regiao, f.entregue_no_prazo, to_char(f.purchased_at, 'YYYY-MM') as mes
    from marts.fato_pedidos f
    join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
    where f.purchased_at::date between %(inicio)s and %(fim)s
      and f.entregue_no_prazo is not null
"""
_TAXA_ATRASO = "avg(case when not entregue_no_prazo then 1.0 else 0.0 end)"
# Itens do periodo pela data de compra do pedido (dim_tempo, como o Power BI).
_ITENS = """
    select i.order_id, i.valor_item, i.produto_sk, i.vendedor_sk, t.ano_mes as mes
    from marts.fato_itens_pedido i
    join marts.dim_tempo t on t.tempo_sk = i.tempo_sk_compra
    where t.data between %(inicio)s and %(fim)s
"""


def cartoes_entrega(conexao, f: Filtros) -> pd.DataFrame:
    sql = f"""
    with base as ({_ENTREGUES}),
    risco as (
        select count(*) as pedidos_alerta, sum(p2.valor_total) as receita_risco
        from marts.previsao_atraso r
        join marts.fato_pedidos p2 on p2.pedido_sk = r.pedido_sk
        where r.alerta and r.conjunto in ('teste', 'em_andamento')
          and p2.purchased_at::date between %(inicio)s and %(fim)s
    )
    select {_TAXA_ATRASO} as taxa_atraso,
           {_TAXA_ATRASO} filter (where mes = %(ref)s) as taxa_ref,
           {_TAXA_ATRASO} filter (where mes = %(ant)s) as taxa_ant,
           (select pedidos_alerta from risco) as pedidos_alerta,
           (select receita_risco from risco) as receita_risco
    from base
    having count(*) > 0
    """
    return _consulta(conexao, sql, _sem_regiao(f))


def taxa_por_regiao(conexao, f: Filtros) -> pd.DataFrame:
    sql = f"""
    with base as ({_ENTREGUES})
    select regiao, {_TAXA_ATRASO} as taxa_atraso,
           (select {_TAXA_ATRASO} from base) as taxa_nacional
    from base
    where regiao is not null
    group by regiao
    order by taxa_atraso desc
    """
    return _consulta(conexao, sql, _sem_regiao(f))


def excesso_por_uf(conexao, f: Filtros) -> pd.DataFrame:
    """Atrasos da UF menos o que a taxa nacional preveria para os entregues dela."""
    sql = f"""
    with base as ({_ENTREGUES}),
    nacional as (select {_TAXA_ATRASO} as taxa from base)
    select b.uf,
           sum(case when not b.entregue_no_prazo then 1 else 0 end) - count(*) * max(n.taxa)
               as atraso_em_excesso
    from base b cross join nacional n
    group by b.uf
    order by atraso_em_excesso desc, b.uf
    """
    return _consulta(conexao, sql, _sem_regiao(f))


def pedidos_em_risco(conexao, f: Filtros) -> pd.DataFrame:
    sql = """
    select '#' || left(p.order_id, 10) as pedido,
           p.purchased_at::date as compra,
           p.estimated_delivery_at::date as entrega_prevista,
           c.uf, p.valor_total as valor, r.prob_atraso
    from marts.previsao_atraso r
    join marts.fato_pedidos p on p.pedido_sk = r.pedido_sk
    join marts.dim_clientes c on c.cliente_sk = p.cliente_sk
    where r.conjunto = 'em_andamento'
      and p.purchased_at::date between %(inicio)s and %(fim)s
    order by r.prob_atraso desc
    limit 50
    """
    return _consulta(conexao, sql, _sem_regiao(f))


def cartoes_vendedores(conexao, f: Filtros) -> pd.DataFrame:
    sql = f"""
    with itens as ({_ITENS}),
    pedidos as (
        select p.entregue_no_prazo from marts.fato_pedidos p
        where p.entregue_no_prazo is not null
          and p.order_id in (select order_id from itens)
    )
    select sum(valor_item) as receita_itens,
           count(*) as itens,
           (select {_TAXA_ATRASO} from pedidos) as taxa_atraso_itens,
           sum(valor_item) filter (where mes = %(ref)s) as receita_ref,
           sum(valor_item) filter (where mes = %(ant)s) as receita_ant
    from itens
    having count(*) > 0
    """
    return _consulta(conexao, sql, _sem_regiao(f))


def receita_por_grupo(conexao, f: Filtros) -> pd.DataFrame:
    sql = f"""
    select d.categoria_grupo, sum(i.valor_item) as receita_itens
    from ({_ITENS}) i
    join marts.dim_produtos d on d.produto_sk = i.produto_sk
    group by d.categoria_grupo
    order by receita_itens desc, d.categoria_grupo
    """
    return _consulta(conexao, sql, _sem_regiao(f))


def vendedores(conexao, f: Filtros) -> pd.DataFrame:
    """Os 50 vendedores de maior receita de itens; a taxa e dos pedidos que tem itens dele."""
    sql = f"""
    with itens as ({_ITENS}),
    por_vendedor as (
        select vendedor_sk, sum(valor_item) as receita_itens, count(*) as itens
        from itens group by vendedor_sk
        order by receita_itens desc, vendedor_sk
        limit 50
    ),
    atraso as (
        select i.vendedor_sk, {_TAXA_ATRASO} as taxa_atraso_itens
        from (select distinct vendedor_sk, order_id from itens) i
        join marts.fato_pedidos p on p.order_id = i.order_id
        where p.entregue_no_prazo is not null
          and i.vendedor_sk in (select vendedor_sk from por_vendedor)
        group by i.vendedor_sk
    )
    select v.vendedor_rotulo as vendedor, pv.receita_itens, pv.itens, a.taxa_atraso_itens
    from por_vendedor pv
    join marts.dim_vendedores v on v.vendedor_sk = pv.vendedor_sk
    left join atraso a on a.vendedor_sk = pv.vendedor_sk
    order by pv.receita_itens desc, v.vendedor_rotulo
    """
    return _consulta(conexao, sql, _sem_regiao(f))
