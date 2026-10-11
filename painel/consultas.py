"""Consultas do painel: uma funcao por visual, (conexao, filtros) -> DataFrame.

As definicoes repetem as medidas DAX do Power BI (Etapa 5) e sao conferidas contra
dashboards/powerbi/conferencia/esperado.sql nos testes de integracao. Filtro vai
sempre como parametro nomeado, nunca no texto do SQL.
"""
from __future__ import annotations

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
