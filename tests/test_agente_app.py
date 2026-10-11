"""Interface Streamlit com banco, modelo e fluxo substituidos (AppTest)."""
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from agente.agente import Resposta

APP = str(Path(__file__).resolve().parents[1] / "agente" / "app.py")


class _Chamadas:
    def __init__(self, resposta):
        self.resposta = resposta
        self.perguntas = []

    def __call__(self, pergunta, historico, llm, executar, esquema):
        self.perguntas.append(pergunta)
        return self.resposta


class _Conexao:
    abertas = []

    def __init__(self):
        self.fechada = False
        _Conexao.abertas.append(self)

    def close(self):
        self.fechada = True


@pytest.fixture()
def ambiente(monkeypatch):
    st.cache_resource.clear()
    st.cache_data.clear()
    _Conexao.abertas = []
    monkeypatch.setattr("agente.banco.abrir_conexao", _Conexao)
    monkeypatch.setattr("agente.banco.ler_atualizacao", lambda conexao: "Dados processados em 09/10/2026")
    monkeypatch.setattr("agente.llm.provedores_do_ambiente", lambda: [])
    chamadas = _Chamadas(Resposta("ok", "Foram 99.441 pedidos.", sql="SELECT 1", colunas=["pedidos"],
                                  linhas=[(99441,)], confirmada=True))
    monkeypatch.setattr("agente.agente.responder", chamadas)
    return chamadas


# A conversa agora e a pagina "Pergunte aos dados" do painel.
PERGUNTE = """
from agente.app import barra_lateral, preparar
from painel.paginas import pergunte
preparar()
pergunte.pagina()
barra_lateral()
"""


def _app():
    return AppTest.from_string(PERGUNTE, default_timeout=30).run()


def test_tela_inicial(ambiente):
    at = _app()
    assert not at.exception
    assert any("O que você quer saber" in m.value for m in at.markdown)
    assert any("SQL" in c.value for c in at.caption)
    assert len([b for b in at.button if b.key and b.key.startswith("exemplo_")]) == 4


def test_tema_comeca_escuro_e_alterna(ambiente):
    at = _app()
    assert at.session_state["tema"] == "escuro"
    at.button(key="alternar_tema").click().run()
    assert at.session_state["tema"] == "claro"
    at.button(key="alternar_tema").click().run()
    assert at.session_state["tema"] == "escuro"


def test_pergunta_aparece_na_barra_lateral(ambiente):
    at = _app()
    at.chat_input[0].set_value("Quantos pedidos?").run()
    assert any("Quantos pedidos?" in c.value for c in at.sidebar.caption)


def test_nova_conversa_limpa_tudo(ambiente):
    at = _app()
    at.chat_input[0].set_value("Quantos pedidos?").run()
    at.button(key="nova_conversa").click().run()
    assert at.session_state["conversa"] == []
    assert at.session_state["historico"] == []
    assert any("O que você quer saber" in m.value for m in at.markdown)


def test_exemplo_clicado_vira_pergunta(ambiente):
    at = _app()
    at.button(key="exemplo_0").click().run()
    assert ambiente.perguntas == ["Qual a receita por ano?"]


def test_pergunta_longa_e_recusada(ambiente):
    at = _app()
    at.chat_input[0].set_value("x" * 301).run()
    assert ambiente.perguntas == []
    assert any("300 caracteres" in w.value for w in at.warning)


def test_limite_por_sessao(ambiente):
    at = _app()
    at.session_state["perguntas_feitas"] = 20
    at.chat_input[0].set_value("Quantos pedidos?").run()
    assert ambiente.perguntas == []
    assert any("limite de 20 perguntas" in w.value for w in at.warning)


def test_resposta_normal_mostra_texto_e_sql(ambiente):
    at = _app()
    at.chat_input[0].set_value("Quantos pedidos?").run()
    assert ambiente.perguntas == ["Quantos pedidos?"]
    assert any("99.441" in m.value for m in at.markdown)
    assert any(c.value == "SELECT 1" for c in at.code)


def test_cota_esgotada(ambiente):
    ambiente.resposta = Resposta("cota", "A cota gratuita do dia acabou. Volte amanhã.")
    at = _app()
    at.chat_input[0].set_value("Quantos pedidos?").run()
    assert any("cota gratuita do dia acabou" in w.value for w in at.warning)


def test_banco_acordando(ambiente, monkeypatch):
    def falha():
        raise OSError("timeout")
    monkeypatch.setattr("agente.banco.abrir_conexao", falha)
    at = _app()
    at.chat_input[0].set_value("Quantos pedidos?").run()
    assert not at.exception
    assert any("banco está acordando" in w.value for w in at.warning)


def test_rodape_com_data_dos_dados(ambiente):
    at = _app()
    assert any("Dados processados em 09/10/2026" in c.value for c in at.caption)


def test_cifrao_escapado_na_resposta(ambiente):
    ambiente.resposta = Resposta("ok", "De R$ 10,00 em 2016 até R$ 20,00 em 2018.", sql="SELECT 1",
                                 colunas=["ano", "receita"], linhas=[(2016, 10.0), (2018, 20.0)],
                                 grafico="barras", confirmada=True)
    at = _app()
    at.chat_input[0].set_value("Receita por ano?").run()
    assert not at.exception
    assert any(r"\$ 10,00" in m.value for m in at.markdown)


def test_botao_de_tema_fica_na_barra_lateral(ambiente):
    at = _app()
    chaves = [b.key for b in at.sidebar.button]
    assert "alternar_tema" in chaves and "nova_conversa" in chaves
    assert "alternar_tema" not in [b.key for b in at.main.button]


def test_conexao_aberta_e_fechada_a_cada_pergunta(ambiente):
    at = _app()
    antes = len(_Conexao.abertas)
    at.chat_input[0].set_value("Quantos pedidos?").run()
    at.chat_input[0].set_value("E em 2018?").run()
    novas = _Conexao.abertas[antes:]
    assert len(novas) == 2 and all(c.fechada for c in novas)


def test_erro_inesperado_no_fluxo_vira_aviso(ambiente, monkeypatch):
    def quebra(*a, **k):
        raise RuntimeError("bug")
    monkeypatch.setattr("agente.agente.responder", quebra)
    at = _app()
    at.chat_input[0].set_value("Quantos pedidos?").run()
    assert not at.exception
    assert any("Algo deu errado" in e.value for e in at.error)


def test_banco_indisponivel_vira_aviso(ambiente):
    ambiente.resposta = Resposta("banco", "O banco está acordando ou a conexão caiu; tente de novo.")
    at = _app()
    at.chat_input[0].set_value("Quantos pedidos?").run()
    assert any("acordando" in w.value for w in at.warning)
