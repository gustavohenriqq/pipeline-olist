"""Paginas do painel com banco e consultas substituidos (AppTest)."""
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from agente.banco import ErroBanco

APP = str(Path(__file__).resolve().parents[1] / "agente" / "app.py")
PAGINA = """
from agente.app import barra_lateral, preparar
from painel.paginas import {modulo} as pagina
preparar()
pagina.pagina()
barra_lateral()
"""

CARTOES_EXECUTIVO = pd.DataFrame([{
    "receita": 15786203.57, "pedidos": 99092, "ticket_medio": 159.31, "pct_no_prazo": 0.932,
    "nota_media": 4.09, "receita_ref": 1003308.47, "receita_ant": 1058728.03, "pedidos_ref": 6512,
    "pedidos_ant": 6292, "ticket_ref": 154.07, "ticket_ant": 168.27, "pct_ref": 0.938,
    "pct_ant": 0.966, "nota_ref": 4.2, "nota_ant": 4.21, "mes_referencia": "2018-08"}])
FIXOS = {
    "cartoes_executivo": CARTOES_EXECUTIVO,
    "receita_mensal": pd.DataFrame({"ano_mes": ["2018-07", "2018-08"], "receita": [1.05e6, 1.0e6],
                                    "receita_ano_anterior": [5.8e5, 6.7e5]}),
    "placar_mensal": pd.DataFrame({"ano_mes": ["2018-08"], "receita": [1.0e6], "variacao_mensal": [-0.052],
                                   "pedidos": [6512], "ticket_medio": [154.07], "pct_no_prazo": [0.938]}),
    "cartoes_entrega": pd.DataFrame([{"taxa_atraso": 0.068, "taxa_ref": 0.062, "taxa_ant": 0.034,
                                      "pedidos_alerta": 8468, "receita_risco": 1.57e6,
                                      "mes_referencia": "2018-08"}]),
    "taxa_por_regiao": pd.DataFrame({"regiao": ["Nordeste", "Sul"], "taxa_atraso": [0.127, 0.059],
                                     "taxa_nacional": [0.068, 0.068]}),
    "excesso_por_uf": pd.DataFrame({"uf": ["RJ", "SP"], "atraso_em_excesso": [659.0, -923.0]}),
    "pedidos_em_risco": pd.DataFrame({"pedido": ["#b6906ad8ff"], "compra": ["2018-07-29"],
                                      "entrega_prevista": ["2018-08-07"], "uf": ["RJ"], "valor": [193.36],
                                      "prob_atraso": [0.525]}),
    "cartoes_vendedores": pd.DataFrame([{"receita_itens": 15786203.57, "itens": 112279,
                                         "taxa_atraso_itens": 0.068, "receita_ref": 1.0e6, "receita_ant": 1.05e6,
                                         "mes_referencia": "2018-08"}]),
    "receita_por_grupo": pd.DataFrame({"categoria_grupo": ["Casa e Decoração"], "receita_itens": [3.2e6]}),
    "vendedores": pd.DataFrame({"vendedor": ["Guariba/SP · 4869f7"], "receita_itens": [249640.70],
                                "itens": [1156], "taxa_atraso_itens": [0.105]}),
}


def _fixa(nome, resultado):
    """Substituto de uma consulta com o mesmo nome (o painel carrega a consulta pelo nome)."""
    def consulta(conexao, f):
        if isinstance(resultado, Exception):
            raise resultado
        return resultado.copy()
    consulta.__name__ = nome
    return consulta


class _Conexao:
    def close(self):
        pass


@pytest.fixture()
def ambiente(monkeypatch):
    st.cache_data.clear()
    st.cache_resource.clear()
    monkeypatch.setattr("agente.banco.abrir_conexao", _Conexao)
    monkeypatch.setattr("agente.banco.ler_atualizacao", lambda conexao: "Dados processados em 09/10/2026")
    monkeypatch.setattr("agente.llm.provedores_do_ambiente", lambda: [])
    for nome, df in FIXOS.items():
        monkeypatch.setattr(f"painel.consultas.{nome}", _fixa(nome, df))
    return monkeypatch


def _pagina(modulo):
    return AppTest.from_string(PAGINA.format(modulo=modulo), default_timeout=30).run()


def _html(at):
    return "\n".join(m.value for m in at.markdown)


def test_menu_abre_na_visao_executiva(ambiente):
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert "Visão executiva" in _html(at)


@pytest.mark.parametrize("modulo", ["executivo", "entrega", "vendedores", "pergunte"])
def test_paginas_abrem_sem_excecao(ambiente, modulo):
    assert not _pagina(modulo).exception


def test_visao_executiva_mostra_cinco_cartoes(ambiente):
    html = _html(_pagina("executivo"))
    assert html.count('class="cartao ') == 5
    assert "R$ 15,79 mi" in html and "ago/2018 contra o mês anterior" in html


def test_entrega_e_vendedores_mostram_tres_cartoes(ambiente):
    assert _html(_pagina("entrega")).count('class="cartao ') == 3
    assert _html(_pagina("vendedores")).count('class="cartao ') == 3


def test_risco_alto_pintado_na_tabela(ambiente):
    assert '<tr class="risco-alto">' in _html(_pagina("entrega"))


def test_consulta_que_falha_nao_derruba_a_pagina(ambiente):
    ambiente.setattr("painel.consultas.receita_mensal",
                     _fixa("receita_mensal", ErroBanco("relation does not exist")))
    at = _pagina("executivo")
    assert not at.exception
    assert any("Não consegui carregar" in w.value for w in at.warning)
    assert _html(at).count('class="cartao ') == 5


def test_banco_acordando_mostra_aviso_e_tentar_de_novo(ambiente):
    def dormindo():
        raise OSError("timeout")
    ambiente.setattr("agente.banco.abrir_conexao", dormindo)
    at = _pagina("executivo")
    assert not at.exception
    assert sum("acordando" in w.value for w in at.warning) == 1
    assert at.button(key="tentar_de_novo")


def test_periodo_sem_dados(ambiente):
    for nome in FIXOS:
        ambiente.setattr(f"painel.consultas.{nome}", _fixa(nome, pd.DataFrame()))
    at = _pagina("executivo")
    html = _html(at)
    assert not at.exception
    assert "sem dados" in html and "Sem pedidos neste período" in html


class _Respostas:
    def __init__(self):
        self.chamadas = []

    def __call__(self, pergunta, historico, llm, executar, esquema, contexto=None):
        from agente.agente import Resposta
        self.chamadas.append({"pergunta": pergunta, "contexto": contexto})
        return Resposta("ok", "Foram 10 pedidos.", sql="SELECT 1", colunas=["pedidos"], linhas=[(10,)],
                        confirmada=True)


@pytest.fixture()
def respostas(ambiente):
    r = _Respostas()
    ambiente.setattr("agente.agente.responder", r)
    return r


def _abrir_agente(at):
    at.button(key="abrir_agente").click().run()
    return at


def test_tire_sua_duvida_abre_e_fecha(respostas):
    at = _abrir_agente(_pagina("entrega"))
    assert at.session_state["agente_aberto"] is True
    assert any(c.key == "pergunta_lateral" for c in at.chat_input)
    at.button(key="abrir_agente").click().run()
    assert at.session_state["agente_aberto"] is False
    assert not any(c.key == "pergunta_lateral" for c in at.chat_input)


def test_pergunta_da_lateral_entra_na_conversa_compartilhada(respostas):
    at = _abrir_agente(_pagina("executivo"))
    at.chat_input(key="pergunta_lateral").set_value("E por UF?").run()
    assert not at.exception
    assert [i["pergunta"] for i in at.session_state["conversa"]] == ["E por UF?"]
    assert any("Foram 10 pedidos" in m.value for m in at.markdown)


def test_responder_recebe_o_contexto_da_pagina_e_dos_filtros(respostas):
    at = _abrir_agente(_pagina("entrega"))
    at.chat_input(key="pergunta_lateral").set_value("Qual UF atrasa mais?").run()
    contexto = respostas.chamadas[-1]["contexto"]
    assert "página Entrega e risco" in contexto and "período 01/01/2017 a 31/08/2018" in contexto
    assert "região" not in contexto
    assert all("Contexto do painel" not in m.value for m in at.markdown)


def test_limite_de_20_soma_lateral_e_pagina(respostas):
    at = _abrir_agente(_pagina("executivo"))
    at.session_state["perguntas_feitas"] = 20
    at.chat_input(key="pergunta_lateral").set_value("Mais uma?").run()
    assert respostas.chamadas == []
    assert any("limite de 20 perguntas" in w.value for w in at.warning)


def test_duas_sessoes_ao_mesmo_tempo_nao_trocam_a_coluna_do_agente(ambiente):
    """Streamlit roda cada visitante numa thread do mesmo processo: nada da tela
    pode ficar em variavel de modulo. A abre o agente; B, ao mesmo tempo, nao."""
    import threading
    import time

    for nome, df in FIXOS.items():
        def lenta(conexao, f, df=df):
            time.sleep(0.8)
            return df.copy()
        lenta.__name__ = nome
        ambiente.setattr(f"painel.consultas.{nome}", lenta)
    st.cache_data.clear()
    resultados = {}

    def visitante(nome, aberto, atraso):
        time.sleep(atraso)
        at = AppTest.from_string(PAGINA.format(modulo="executivo"), default_timeout=60)
        at.session_state["agente_aberto"] = aberto
        resultados[nome] = at.run()

    for ordem in ((("A", True, 0), ("B", False, 0.3)), (("B", False, 0), ("A", True, 0.3))):
        threads = [threading.Thread(target=visitante, args=args) for args in ordem]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        a, b = resultados["A"], resultados["B"]
        assert not a.exception and not b.exception
        assert sum(c.key == "pergunta_lateral" for c in a.chat_input) == 1
        assert sum(c.key == "pergunta_lateral" for c in b.chat_input) == 0
        st.cache_data.clear()


def test_nota_media_com_diferenca_absoluta(ambiente):
    # nota_ref 4,20 contra nota_ant 4,21: o Power BI mostra "▼ 0,01", nao "0,2%".
    assert "▼ 0,01</b>" in _html(_pagina("executivo"))


def test_rotulo_usa_o_mes_de_referencia_dos_cartoes(ambiente):
    df = CARTOES_EXECUTIVO.assign(mes_referencia="2018-07")
    ambiente.setattr("painel.consultas.cartoes_executivo", _fixa("cartoes_executivo", df))
    html = _html(_pagina("executivo"))
    assert "jul/2018 contra o mês anterior" in html and "ago/2018 contra" not in html


def test_entrega_sem_alerta_mostra_zero_e_taxa_sem_dados_sem_destaque(ambiente):
    df = pd.DataFrame([{"taxa_atraso": None, "taxa_ref": None, "taxa_ant": None, "pedidos_alerta": 0,
                        "receita_risco": 0.0, "mes_referencia": "2018-10"}])
    ambiente.setattr("painel.consultas.cartoes_entrega", _fixa("cartoes_entrega", df))
    html = _html(_pagina("entrega"))
    assert "R$ 0,00" in html and '<div class="cartao-valor">0</div>' in html
    assert "sem mês anterior" not in html


def test_banco_fora_desiste_rapido_depois_da_primeira_falha(ambiente):
    tentativas = []

    def dormindo():
        tentativas.append(1)
        raise OSError("timeout")
    ambiente.setattr("agente.banco.abrir_conexao", dormindo)
    at = _pagina("executivo")
    assert not at.exception
    # 3 visuais e o rodape da barra lateral: so a primeira conexao espera o timeout
    assert len(tentativas) == 1
    assert sum("acordando" in w.value for w in at.warning) == 1
    # "Tentar de novo" tenta de verdade na proxima execucao
    at.button(key="tentar_de_novo").click().run()
    assert len(tentativas) == 2
    assert sum("acordando" in w.value for w in at.warning) == 1


TROCA = """
import importlib
import streamlit as st
from agente.app import barra_lateral, preparar
preparar()
importlib.import_module("painel.paginas." + st.session_state.get("_teste_pagina", "entrega")).pagina()
barra_lateral()
"""


def test_regiao_sai_da_url_onde_e_ignorada_e_volta_na_visao_executiva(ambiente):
    at = AppTest.from_string(TROCA, default_timeout=30)
    at.query_params.update({"inicio": "2018-01-01", "fim": "2018-08-31", "regiao": "Nordeste"})
    at.run()
    assert not at.exception
    assert "regiao" not in at.query_params
    assert at.query_params["inicio"] == "2018-01-01"
    assert at.session_state["filtros"].regiao == "Nordeste"
    at.session_state["_teste_pagina"] = "vendedores"
    at.run()
    assert "regiao" not in at.query_params
    at.session_state["_teste_pagina"] = "executivo"
    at.run()
    assert at.query_params["regiao"] == "Nordeste"
    assert at.selectbox(key="regiao").value == "Nordeste"


def _colunas_por_linha(bloco):
    """Quantas colunas tem cada st.columns da arvore (para conferir a disposicao)."""
    from streamlit.testing.v1.element_tree import Block, Column
    contagens = []
    filhos = list(getattr(bloco, "children", {}).values())
    colunas = [f for f in filhos if isinstance(f, Column)]
    if colunas:
        contagens.append(len(colunas))
    for filho in filhos:
        if isinstance(filho, Block):
            contagens.extend(_colunas_por_linha(filho))
    return contagens


def test_entrega_com_agente_aberto_nao_aperta_tres_colunas(ambiente):
    fechado = _pagina("entrega")
    assert 3 in _colunas_por_linha(fechado.main)
    at = AppTest.from_string(PAGINA.format(modulo="entrega"), default_timeout=30)
    at.session_state["agente_aberto"] = True
    at.run()
    assert not at.exception
    assert 3 not in _colunas_por_linha(at.main)
    assert '<tr class="risco-alto">' in _html(at)
