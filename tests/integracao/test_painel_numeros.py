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


TUDO_INICIO, TUDO_FIM = "2016-09-01", "2018-10-31"


@pytest.fixture(scope="module")
def painel_esperado(conexao):
    return _casos(conexao, "painel/conferencia/esperado.sql")


@pytest.fixture(scope="module")
def tudo():
    from datetime import date
    from painel.filtros import Filtros
    return Filtros(date(2016, 9, 1), date(2018, 10, 31), None)


def test_cartoes_de_entrega_batem_com_o_power_bi(conexao, esperado, tudo):
    from painel.consultas import cartoes_entrega
    c = cartoes_entrega(conexao, tudo).iloc[0]
    assert c.pedidos_alerta == int(_valor(esperado, "pedidos_alerta"))
    assert c.receita_risco == pytest.approx(_valor(esperado, "receita_risco"), abs=0.01)


def test_excesso_do_rj_bate_com_o_power_bi(conexao, esperado, painel_esperado, tudo):
    from painel.consultas import excesso_por_uf
    e = excesso_por_uf(conexao, tudo)
    assert e.iloc[0].uf == painel_esperado["primeira_uf_excesso"]
    assert e.set_index("uf").loc["RJ", "atraso_em_excesso"] == pytest.approx(_valor(esperado, "excesso_rj"), abs=1e-6)


def test_taxa_por_regiao_e_nacional(conexao, painel_esperado, tudo):
    from painel.consultas import taxa_por_regiao
    t = taxa_por_regiao(conexao, tudo).set_index("regiao")
    assert t.loc["Nordeste", "taxa_atraso"] == pytest.approx(_valor(painel_esperado, "taxa_regiao_nordeste"), abs=1e-9)
    assert (t["taxa_nacional"] - _valor(painel_esperado, "taxa_nacional")).abs().max() < 1e-9


def test_pedidos_em_risco(conexao, painel_esperado, tudo):
    from painel.consultas import pedidos_em_risco
    r = pedidos_em_risco(conexao, tudo)
    assert len(r) == int(_valor(painel_esperado, "pedidos_em_risco_linhas"))
    assert list(r.prob_atraso) == sorted(r.prob_atraso, reverse=True)
    assert r.pedido.str.match(r"^#[0-9a-f]{10}$").all()


def test_cartoes_de_vendedores(conexao, painel_esperado, tudo):
    from painel.consultas import cartoes_vendedores
    c = cartoes_vendedores(conexao, tudo).iloc[0]
    assert c.itens == int(_valor(painel_esperado, "itens"))
    assert c.receita_itens == pytest.approx(_valor(painel_esperado, "receita_itens"), abs=0.01)
    assert c.taxa_atraso_itens == pytest.approx(_valor(painel_esperado, "taxa_atraso_itens"), abs=1e-9)


def test_receita_por_grupo_e_vendedores(conexao, painel_esperado, tudo):
    from painel.consultas import receita_por_grupo, vendedores
    g = receita_por_grupo(conexao, tudo)
    assert g.iloc[0].categoria_grupo == painel_esperado["primeiro_grupo"]
    assert g.iloc[0].receita_itens == pytest.approx(_valor(painel_esperado, "receita_primeiro_grupo"), abs=0.01)
    v = vendedores(conexao, tudo)
    assert v.iloc[0].vendedor == painel_esperado["primeiro_vendedor"]
    assert len(v) <= 50


def _receita(conexao, inicio, fim):
    with conexao.cursor() as cur:
        cur.execute("select sum(valor_total) from marts.fato_pedidos where purchased_at::date between %s and %s",
                    (inicio, fim))
        valor = cur.fetchone()[0]
    conexao.rollback()
    return float(valor) if valor is not None else None


def test_periodo_no_meio_do_mes_compara_os_mesmos_dias(conexao):
    """1 a 15 de agosto contra 1 a 15 de julho, como o DATEADD do Power BI."""
    from datetime import date
    from painel.consultas import cartoes_executivo, delta, placar_mensal, receita_mensal
    from painel.filtros import Filtros
    f = Filtros(date(2018, 1, 1), date(2018, 8, 15))
    agosto, julho = _receita(conexao, date(2018, 8, 1), date(2018, 8, 15)), _receita(conexao, date(2018, 7, 1),
                                                                                     date(2018, 7, 15))
    if agosto is None or julho is None:
        pytest.skip("sem pedidos nessas quinzenas nesta base")
    c = cartoes_executivo(conexao, f).iloc[0]
    assert delta(c.receita_ref, c.receita_ant, taxa=False) == pytest.approx(agosto / julho - 1, abs=1e-9)
    placar = placar_mensal(conexao, f).set_index("ano_mes")
    assert placar.loc["2018-08", "variacao_mensal"] == pytest.approx(agosto / julho - 1, abs=1e-9)
    ano_anterior = _receita(conexao, date(2017, 8, 1), date(2017, 8, 15))
    r = receita_mensal(conexao, f).set_index("ano_mes")
    assert r.loc["2018-08", "receita_ano_anterior"] == pytest.approx(ano_anterior, abs=0.01)


def test_inicio_no_meio_do_mes_anterior_compara_o_mes_inteiro(conexao):
    from datetime import date
    from painel.consultas import cartoes_executivo, delta
    from painel.filtros import Filtros
    c = cartoes_executivo(conexao, Filtros(date(2018, 7, 20), date(2018, 8, 31))).iloc[0]
    agosto, julho = _receita(conexao, date(2018, 8, 1), date(2018, 8, 31)), _receita(conexao, date(2018, 7, 1),
                                                                                     date(2018, 7, 31))
    if agosto is None or julho is None:
        pytest.skip("sem pedidos nesses meses nesta base")
    assert delta(c.receita_ref, c.receita_ant, taxa=False) == pytest.approx(agosto / julho - 1, abs=1e-9)
