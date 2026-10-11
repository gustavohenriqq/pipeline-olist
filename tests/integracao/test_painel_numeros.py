"""Numeros do painel contra o banco (local ou CI) e contra o esperado do Power BI.

Os casos de dashboards/powerbi/conferencia/esperado.sql sao a mesma referencia que
confere o modelo do Power BI: se o painel web divergir, este teste acusa.
"""
from pathlib import Path

import psycopg2
import pytest

from agente.banco import executar
from ingestion.config import PG

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def conexao():
    try:
        conn = psycopg2.connect(**PG)
    except psycopg2.OperationalError:
        pytest.skip("Postgres indisponivel")
    yield conn
    conn.close()


def test_executar_com_parametro(conexao):
    assert executar(conexao, "select %s::int + 1 as n", (41,)) == (["n"], [(42,)])


def _casos(conexao, arquivo):
    with conexao.cursor() as cur:
        cur.execute((RAIZ / arquivo).read_text(encoding="utf-8"))
        linhas = cur.fetchall()
    conexao.rollback()
    return {caso: valor for caso, valor in linhas}


@pytest.fixture(scope="module")
def esperado(conexao):
    return _casos(conexao, "dashboards/powerbi/conferencia/esperado.sql")


def _valor(esperado, caso):
    valor = esperado.get(caso)
    if valor in (None, "vazio"):
        pytest.skip(f"caso {caso} sem valor nesta base (amostra do CI?)")
    return float(valor)


def test_cartoes_na_base_inteira_batem_com_o_power_bi(conexao, esperado):
    from painel.consultas import cartoes_executivo
    from painel.filtros import Filtros
    from datetime import date
    c = cartoes_executivo(conexao, Filtros(date(2016, 9, 1), date(2018, 10, 31), None)).iloc[0]
    assert c.pedidos == int(_valor(esperado, "pedidos"))
    assert c.receita == pytest.approx(_valor(esperado, "receita"), abs=0.01)
    assert c.ticket_medio == pytest.approx(_valor(esperado, "ticket_medio"), abs=0.0001)
    assert c.pct_no_prazo == pytest.approx(_valor(esperado, "pct_no_prazo"), abs=1e-9)
    assert c.nota_media == pytest.approx(_valor(esperado, "nota_media"), abs=1e-9)


def test_destaques_da_janela_padrao(conexao, esperado):
    from painel.consultas import cartoes_executivo, delta
    from painel.filtros import PADRAO
    c = cartoes_executivo(conexao, PADRAO).iloc[0]
    assert delta(c.receita_ref, c.receita_ant, taxa=False) == pytest.approx(
        _valor(esperado, "delta_receita_janela"), abs=1e-9)
    assert delta(c.pct_ref, c.pct_ant, taxa=True) == pytest.approx(
        _valor(esperado, "delta_pct_no_prazo_janela"), abs=1e-9)


def test_variacao_mensal_de_marco(conexao, esperado):
    from painel.consultas import placar_mensal
    from painel.filtros import Filtros
    from datetime import date
    p = placar_mensal(conexao, Filtros(date(2016, 9, 1), date(2018, 10, 31), None)).set_index("ano_mes")
    assert p.loc["2018-03", "variacao_mensal"] == pytest.approx(_valor(esperado, "variacao_mensal_2018_03"), abs=1e-9)


def test_receita_mensal_tem_o_ano_anterior(conexao):
    from painel.consultas import receita_mensal
    from painel.filtros import PADRAO
    r = receita_mensal(conexao, PADRAO).set_index("ano_mes")
    assert r.loc["2018-03", "receita_ano_anterior"] == pytest.approx(r.loc["2017-03", "receita"], abs=0.01)
