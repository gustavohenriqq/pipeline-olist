"""Pergunte aos dados: a conversa com o agente em pagina inteira.

`processar` e `mostrar` tambem servem a coluna "Tire sua duvida" das outras paginas:
a conversa e uma so por sessao.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from agente import agente as nucleo
from agente import banco
from agente import llm as modelo
from agente.apresentacao import escapar_markdown, grafico, preparar, tabela_html
from agente.config import MAX_PERGUNTA, MAX_POR_SESSAO
from agente.tema import PALETAS
from painel.comum import ICONE

ESQUEMA = (Path(__file__).resolve().parents[2] / "agente" / "esquema_marts.md").read_text(encoding="utf-8")
# (rotulo do chip, pergunta enviada, icone)
EXEMPLOS = [
    ("Receita por ano", "Qual a receita por ano?", ":material/payments:"),
    ("Atraso por UF", "Quais as 5 UFs com maior taxa de atraso?", ":material/local_shipping:"),
    ("Pedidos em 2018", "Mostre a evolução mensal de pedidos em 2018", ":material/show_chart:"),
    ("Alertas de atraso", "Quantos pedidos em andamento estão em alerta de atraso?",
     ":material/notifications_active:"),
]


@st.cache_resource
def _cliente():
    return modelo.ClienteLLM(modelo.provedores_do_ambiente())


def _usar_exemplo(pergunta: str) -> None:
    st.session_state.pendente = pergunta


def mostrar(item: dict, compacto: bool = False) -> None:
    """Uma pergunta e a resposta; no modo compacto (coluna lateral) sem grafico."""
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(escapar_markdown(item["pergunta"]))
    with st.chat_message("assistant", avatar=":material/insights:"):
        r: nucleo.Resposta = item["resposta"]
        texto = escapar_markdown(r.texto)
        if r.tipo == "cota":
            st.warning(texto)
        elif r.tipo in ("erro", "recusado"):
            st.error(texto)
        elif r.tipo == "fora_do_escopo":
            st.info(f"Essa pergunta está fora do que a base tem: {texto}")
        elif r.confirmada or r.tipo == "vazio":
            st.markdown(texto)
        else:
            st.warning(texto)
        if r.linhas:
            df = preparar(pd.DataFrame(r.linhas, columns=r.colunas))
            if r.grafico and not compacto:
                st.altair_chart(grafico(df, r.grafico, PALETAS[st.session_state.tema]),
                                width="stretch", theme=None)
            st.markdown(tabela_html(df.head(10) if compacto else df), unsafe_allow_html=True)
        if r.sql:
            with st.expander("SQL gerado", icon=":material/code:"):
                st.code(r.sql, language="sql")


def processar(pergunta: str, contexto: str | None = None) -> None:
    estado = st.session_state
    if len(pergunta) > MAX_PERGUNTA:
        st.warning(f"A pergunta passa de {MAX_PERGUNTA} caracteres; resuma um pouco.")
        return
    if estado.perguntas_feitas >= MAX_POR_SESSAO:
        st.warning(f"Você chegou ao limite de {MAX_POR_SESSAO} perguntas desta sessão. "
                   "A cota do modelo é gratuita e compartilhada; volte mais tarde.")
        return
    # Uma conexao por pergunta: uma conexao guardada morre quando o Neon dorme
    # e, compartilhada entre visitantes, misturaria transacoes.
    try:
        conexao = banco.abrir_conexao()
    except Exception:  # noqa: BLE001
        st.warning("O banco está acordando; tente de novo em alguns segundos.")
        return
    estado.perguntas_feitas += 1
    try:
        with st.spinner("Consultando os dados..."):
            resposta = nucleo.responder(pergunta, estado.historico, _cliente(),
                                        lambda sql: banco.executar(conexao, sql), ESQUEMA)
    except Exception:  # noqa: BLE001 (ultima defesa: nada chega cru na tela)
        resposta = nucleo.Resposta("erro", "Algo deu errado ao responder; tente de novo.")
    finally:
        conexao.close()
    estado.conversa.append({"pergunta": pergunta, "resposta": resposta})
    if resposta.sql and resposta.tipo in ("ok", "vazio"):
        estado.historico.append(nucleo.Turno(pergunta, resposta.sql))


def _tela_vazia() -> None:
    with st.container(key="vazio"):
        st.markdown(f'<div class="hero"><div class="hero-icone">{ICONE.format(t=32)}</div>'
                    '<h1>Olá! O que você quer saber sobre as <span class="destaque">vendas</span>?</h1>'
                    "</div>", unsafe_allow_html=True)
        with st.container(key="chips", horizontal=True, horizontal_alignment="center"):
            for i, (rotulo, pergunta, icone) in enumerate(EXEMPLOS):
                st.button(rotulo, key=f"exemplo_{i}", icon=icone, on_click=_usar_exemplo, args=(pergunta,))
        st.caption("Escreva uma pergunta de negócio em português. Ela vira uma consulta SQL nas tabelas "
                   "do projeto; cada resposta mostra a tabela e o SQL gerado. Se um número da frase não "
                   "bater com o resultado, a frase é descartada.")
        st.markdown('<div class="pilha"><span>dbt</span><span>PostgreSQL</span><span>Python</span>'
                    "<span>Streamlit</span></div>", unsafe_allow_html=True)


def pagina() -> None:
    st.session_state.pagina_atual = "Pergunte aos dados"
    pergunta = st.chat_input("Pergunte sobre receita, pedidos, atrasos, avaliações...") \
        or st.session_state.pop("pendente", None)
    if pergunta:
        processar(pergunta.strip())
    if st.session_state.conversa:
        for item in st.session_state.conversa:
            mostrar(item)
    else:
        _tela_vazia()
