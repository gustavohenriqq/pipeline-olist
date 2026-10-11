"""Interface do agente (Streamlit). Desenha o que agente.responder devolve.

Rodar local:  streamlit run agente/app.py
No Streamlit Community Cloud, as chaves e a conexao vem de st.secrets.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
# A raiz vai na frente da pasta do script; senao "agente" resolve para agente/agente.py.
if str(RAIZ) in sys.path:
    sys.path.remove(str(RAIZ))
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from agente import agente as nucleo  # noqa: E402
from agente import banco  # noqa: E402
from agente import llm as modelo  # noqa: E402
from agente.apresentacao import escapar_markdown, grafico, preparar, tabela_html  # noqa: E402
from agente.config import MAX_PERGUNTA, MAX_POR_SESSAO  # noqa: E402
from agente.tema import PALETAS, css, tema_valido  # noqa: E402

ESQUEMA = (Path(__file__).resolve().parent / "esquema_marts.md").read_text(encoding="utf-8")
REPO = "https://github.com/gustavohenriqq/pipeline-olist"
# (rotulo do chip, pergunta enviada, icone)
EXEMPLOS = [
    ("Receita por ano", "Qual a receita por ano?", ":material/payments:"),
    ("Atraso por UF", "Quais as 5 UFs com maior taxa de atraso?", ":material/local_shipping:"),
    ("Pedidos em 2018", "Mostre a evolução mensal de pedidos em 2018", ":material/show_chart:"),
    ("Alertas de atraso", "Quantos pedidos em andamento estão em alerta de atraso?",
     ":material/notifications_active:"),
]
ICONE = ('<svg width="{t}" height="{t}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.2" stroke-linecap="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>')


def _carregar_segredos() -> None:
    """No Streamlit Cloud os segredos ficam em st.secrets; o resto do codigo le o ambiente."""
    try:
        for chave, valor in st.secrets.items():
            os.environ.setdefault(chave, str(valor))
    except Exception:  # noqa: BLE001 (sem secrets.toml local)
        pass


@st.cache_resource
def _conexao():
    return banco.abrir_conexao()


@st.cache_resource
def _cliente():
    return modelo.ClienteLLM(modelo.provedores_do_ambiente())


def _alternar_tema() -> None:
    estado = st.session_state
    estado.tema = "escuro" if estado.tema == "claro" else "claro"
    st.query_params["tema"] = estado.tema


def _nova_conversa() -> None:
    # perguntas_feitas fica: o limite e por sessao, nao por conversa.
    st.session_state.conversa = []
    st.session_state.historico = []


def _usar_exemplo(pergunta: str) -> None:
    st.session_state.pendente = pergunta


def _mostrar(item: dict) -> None:
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
            if r.grafico:
                st.altair_chart(grafico(df, r.grafico, PALETAS[st.session_state.tema]),
                                use_container_width=True, theme=None)
            st.markdown(tabela_html(df), unsafe_allow_html=True)
        if r.sql:
            with st.expander("SQL gerado", icon=":material/code:"):
                st.code(r.sql, language="sql")


def _processar(pergunta: str) -> None:
    estado = st.session_state
    if len(pergunta) > MAX_PERGUNTA:
        st.warning(f"A pergunta passa de {MAX_PERGUNTA} caracteres; resuma um pouco.")
        return
    if estado.perguntas_feitas >= MAX_POR_SESSAO:
        st.warning(f"Você chegou ao limite de {MAX_POR_SESSAO} perguntas desta sessão. "
                   "A cota do modelo é gratuita e compartilhada; volte mais tarde.")
        return
    try:
        conexao = _conexao()
    except Exception:  # noqa: BLE001
        st.warning("O banco está acordando; tente de novo em alguns segundos.")
        return
    estado.perguntas_feitas += 1
    with st.spinner("Consultando os dados..."):
        resposta = nucleo.responder(pergunta, estado.historico, _cliente(),
                                    lambda sql: banco.executar(conexao, sql), ESQUEMA)
    estado.conversa.append({"pergunta": pergunta, "resposta": resposta})
    if resposta.sql and resposta.tipo in ("ok", "vazio"):
        estado.historico.append(nucleo.Turno(pergunta, resposta.sql))


def _topo() -> None:
    marca, botao = st.columns([1, 0.06], vertical_alignment="center")
    marca.markdown(f'<div class="marca"><span class="marca-icone">{ICONE.format(t=18)}</span>'
                   "Pergunte aos dados</div>", unsafe_allow_html=True)
    escuro = st.session_state.tema == "escuro"
    botao.button("", key="alternar_tema", on_click=_alternar_tema, type="tertiary",
                 icon=":material/light_mode:" if escuro else ":material/dark_mode:",
                 help="Tema claro" if escuro else "Tema escuro")


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


def _barra_lateral() -> None:
    with st.sidebar:
        st.button("Nova conversa", key="nova_conversa", icon=":material/edit_square:",
                  on_click=_nova_conversa, use_container_width=True)
        st.markdown('<div class="rotulo-secao">Nesta conversa</div>', unsafe_allow_html=True)
        perguntas = [item["pergunta"] for item in st.session_state.conversa]
        if not perguntas:
            st.caption("As perguntas desta conversa aparecem aqui.")
        for pergunta in reversed(perguntas):
            st.caption(escapar_markdown(pergunta if len(pergunta) <= 60 else pergunta[:57] + "..."))
        st.markdown('<div class="rotulo-secao">Sobre</div>', unsafe_allow_html=True)
        st.markdown(f":material/menu_book: [Como o agente funciona]({REPO}/blob/main/docs/agente.md)  \n"
                    f":material/code: [Código no GitHub]({REPO})")
        st.markdown('<div class="rotulo-secao">Dados</div>', unsafe_allow_html=True)
        try:
            resumo = banco.ler_atualizacao(_conexao())
        except Exception:  # noqa: BLE001
            resumo = None
        partes = [resumo, "Base pública Olist, pedidos de set/2016 a out/2018",
                  "As perguntas não são gravadas"]
        st.caption(" · ".join(p for p in partes if p))


st.set_page_config(page_title="Pergunte aos dados | Olist", page_icon="🔎", layout="wide",
                   initial_sidebar_state="expanded")
_carregar_segredos()
for chave, inicial in (("historico", []), ("conversa", []), ("perguntas_feitas", 0)):
    st.session_state.setdefault(chave, inicial)
st.session_state.setdefault("tema", tema_valido(st.query_params.get("tema")))
st.html(f"<style>{css(st.session_state.tema)}</style>")

_topo()
pergunta = st.chat_input("Pergunte sobre receita, pedidos, atrasos, avaliações...") \
    or st.session_state.pop("pendente", None)
if pergunta:
    _processar(pergunta.strip())

if st.session_state.conversa:
    for item in st.session_state.conversa:
        _mostrar(item)
else:
    _tela_vazia()

_barra_lateral()
