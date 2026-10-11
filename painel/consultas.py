"""Consultas do painel: uma funcao por visual, (conexao, filtros) -> DataFrame.

As definicoes repetem as medidas DAX do Power BI (Etapa 5) e sao conferidas contra
dashboards/powerbi/conferencia/esperado.sql nos testes de integracao. Filtro vai
sempre como parametro nomeado, nunca no texto do SQL.
"""
from __future__ import annotations

from dataclasses import replace

import pandas as pd

from agente.banco import executar
from painel.filtros import Filtros, janela_comparacao

# Pedidos do periodo, com a regiao do cliente opcional. Base de quase tudo no painel.
_PEDIDOS = """
    select f.order_id, f.valor_total, f.entregue_no_prazo, f.nota_avaliacao,
           to_char(f.purchased_at, 'YYYY-MM') as mes
    from marts.fato_pedidos f
    left join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
    where f.purchased_at::date between %(inicio)s and %(fim)s
      and (%(regiao)s::text is null or c.regiao = %(regiao)s)
"""
# Pedidos da janela de comparacao (mes de referencia e os mesmos dias um mes antes),
# sem o corte do periodo: o mes anterior pode estar fora dele.
_COMPARACAO = """
    select f.order_id, f.valor_total, f.entregue_no_prazo, f.nota_avaliacao,
           f.purchased_at::date as dia
    from marts.fato_pedidos f
    left join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
    where f.purchased_at::date between %(ant_ini)s and %(ref_fim)s
      and (%(regiao)s::text is null or c.regiao = %(regiao)s)
"""
_REF = "dia between %(ref_ini)s and %(ref_fim)s"
_ANT = "dia between %(ant_ini)s and %(ant_fim)s"


# Receita por dia, sem o corte do periodo e com a regiao (uns 700 dias): as janelas
# deslocadas (mes e ano anteriores) somam em cima dela, sem varrer o fato por mes.
_DIARIO = """
    select f.purchased_at::date as dia, sum(f.valor_total) as receita
    from marts.fato_pedidos f
    left join marts.dim_clientes c on c.cliente_sk = f.cliente_sk
    where (%(regiao)s::text is null or c.regiao = %(regiao)s)
    group by 1
"""


def _receita_entre(ini: str, fim: str) -> str:
    """Receita entre duas datas (expressoes SQL), lida do CTE diario."""
    return f"(select sum(d.receita) from diario d where d.dia between {ini} and {fim})"


# Dias de cada mes que estao no periodo, e esses dias um mes e um ano antes.
# Como o DATEADD do Power BI: fim de mes vira fim de mes (31/03 -> 28/02).
_JANELAS_POR_MES = """
    select ano_mes, ini, fim,
           (ini - interval '1 month')::date as mes_ant_ini,
           case when fim = (date_trunc('month', fim) + interval '1 month - 1 day')::date
                then (date_trunc('month', fim) - interval '1 day')::date
                else (fim - interval '1 month')::date end as mes_ant_fim,
           (ini - interval '1 year')::date as ano_ant_ini,
           case when fim = (date_trunc('month', fim) + interval '1 month - 1 day')::date
                then (date_trunc('month', fim - interval '1 year') + interval '1 month - 1 day')::date
                else (fim - interval '1 year')::date end as ano_ant_fim
    from (
        select ano_mes,
               greatest(%(inicio)s::date, to_date(ano_mes, 'YYYY-MM')) as ini,
               least(%(fim)s::date, (to_date(ano_mes, 'YYYY-MM') + interval '1 month - 1 day')::date) as fim
        from periodo
    ) j
"""
_PCT_NO_PRAZO = "avg(case when entregue_no_prazo then 1.0 else 0.0 end) filter (where entregue_no_prazo is not null)"


def _parametros(f: Filtros) -> dict:
    ref_ini, ref_fim, ant_ini, ant_fim = janela_comparacao(f)
    return {"inicio": f.inicio, "fim": f.fim, "regiao": f.regiao,
            "ref_ini": ref_ini, "ref_fim": ref_fim, "ant_ini": ant_ini, "ant_fim": ant_fim}


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
    with base as ({_PEDIDOS}),
    comp as ({_COMPARACAO}),
    total as (
        select sum(valor_total) as receita,
               count(distinct order_id) as pedidos,
               sum(valor_total) / nullif(count(distinct order_id), 0) as ticket_medio,
               {_PCT_NO_PRAZO} as pct_no_prazo,
               avg(nota_avaliacao) as nota_media
        from base
        having count(*) > 0
    ),
    destaque as (
        select sum(valor_total) filter (where {_REF}) as receita_ref,
               sum(valor_total) filter (where {_ANT}) as receita_ant,
               count(distinct order_id) filter (where {_REF}) as pedidos_ref,
               count(distinct order_id) filter (where {_ANT}) as pedidos_ant,
               sum(valor_total) filter (where {_REF})
                   / nullif(count(distinct order_id) filter (where {_REF}), 0) as ticket_ref,
               sum(valor_total) filter (where {_ANT})
                   / nullif(count(distinct order_id) filter (where {_ANT}), 0) as ticket_ant,
               avg(case when entregue_no_prazo then 1.0 else 0.0 end)
                   filter (where entregue_no_prazo is not null and {_REF}) as pct_ref,
               avg(case when entregue_no_prazo then 1.0 else 0.0 end)
                   filter (where entregue_no_prazo is not null and {_ANT}) as pct_ant,
               avg(nota_avaliacao) filter (where {_REF}) as nota_ref,
               avg(nota_avaliacao) filter (where {_ANT}) as nota_ant
        from comp
    )
    select * from total cross join destaque
    """
    return _consulta(conexao, sql, f)


def receita_mensal(conexao, f: Filtros) -> pd.DataFrame:
    """Receita do mes no periodo e dos mesmos dias um ano antes."""
    sql = f"""
    with periodo as (
        select mes as ano_mes, sum(valor_total) as receita from ({_PEDIDOS}) p group by 1
    ),
    janelas as ({_JANELAS_POR_MES}),
    diario as materialized ({_DIARIO})
    select p.ano_mes, p.receita, {_receita_entre("j.ano_ant_ini", "j.ano_ant_fim")} as receita_ano_anterior
    from periodo p
    join janelas j on j.ano_mes = p.ano_mes
    order by p.ano_mes
    """
    return _consulta(conexao, sql, f)


def placar_mensal(conexao, f: Filtros) -> pd.DataFrame:
    """Placar por mes; a variacao compara os mesmos dias um mes antes (mes parcial com parcial)."""
    sql = f"""
    with periodo as (
        select mes as ano_mes, sum(valor_total) as receita, count(distinct order_id) as pedidos,
               sum(valor_total) / nullif(count(distinct order_id), 0) as ticket_medio,
               {_PCT_NO_PRAZO} as pct_no_prazo
        from ({_PEDIDOS}) p
        group by 1
    ),
    janelas as ({_JANELAS_POR_MES}),
    diario as materialized ({_DIARIO})
    select p.ano_mes, p.receita,
           p.receita / nullif({_receita_entre("j.mes_ant_ini", "j.mes_ant_fim")}, 0) - 1 as variacao_mensal,
           p.pedidos, p.ticket_medio, p.pct_no_prazo
    from periodo p
    join janelas j on j.ano_mes = p.ano_mes
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
    comp as (
        select f.entregue_no_prazo, f.purchased_at::date as dia
        from marts.fato_pedidos f
        where f.purchased_at::date between %(ant_ini)s and %(ref_fim)s
          and f.entregue_no_prazo is not null
    ),
    risco as (
        select count(*) as pedidos_alerta, sum(p2.valor_total) as receita_risco
        from marts.previsao_atraso r
        join marts.fato_pedidos p2 on p2.pedido_sk = r.pedido_sk
        where r.alerta and r.conjunto in ('teste', 'em_andamento')
          and p2.purchased_at::date between %(inicio)s and %(fim)s
    )
    select {_TAXA_ATRASO} as taxa_atraso,
           (select {_TAXA_ATRASO} filter (where {_REF}) from comp) as taxa_ref,
           (select {_TAXA_ATRASO} filter (where {_ANT}) from comp) as taxa_ant,
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
    comp as (
        select i.valor_item, t.data as dia
        from marts.fato_itens_pedido i
        join marts.dim_tempo t on t.tempo_sk = i.tempo_sk_compra
        where t.data between %(ant_ini)s and %(ref_fim)s
    ),
    pedidos as (
        select p.entregue_no_prazo from marts.fato_pedidos p
        where p.entregue_no_prazo is not null
          and p.order_id in (select order_id from itens)
    )
    select sum(valor_item) as receita_itens,
           count(*) as itens,
           (select {_TAXA_ATRASO} from pedidos) as taxa_atraso_itens,
           (select sum(valor_item) filter (where {_REF}) from comp) as receita_ref,
           (select sum(valor_item) filter (where {_ANT}) from comp) as receita_ant
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
