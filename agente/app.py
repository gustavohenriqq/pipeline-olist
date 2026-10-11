"""Interface do agente (Streamlit). Desenha o que agente.responder devolve.

Rodar local:  streamlit run agente/app.py
No Streamlit Community Cloud, as chaves e a conexao vem de st.secrets.
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from agente import agente as nucleo  # noqa: E402
from agente import banco  # noqa: E402
from agente import llm as modelo  # noqa: E402
from agente.config import MAX_PERGUNTA, MAX_POR_SESSAO  # noqa: E402

ESQUEMA = (Path(__file__).resolve().parent / "esquema_marts.md").read_text(encoding="utf-8")
EXEMPLOS = [
    "Qual a receita por ano?",
    "Quais as 5 UFs com maior taxa de atraso?",
    "Mostre a evolução mensal de pedidos em 2018",
    "Quantos pedidos em andamento estão em alerta de atraso?",
]


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


def _numerico(df: pd.DataFrame) -> pd.DataFrame:
    """Decimal do psycopg2 vira float para tabela e grafico."""
    saida = df.copy()
    for coluna in saida.columns:
        valores = saida[coluna].dropna()
        if len(valores) and all(isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)
                                for v in valores):
            saida[coluna] = saida[coluna].astype(float)
    return saida


def _grafico(df: pd.DataFrame, tipo: str | None) -> None:
    if tipo is None:
        return
    eixo = next((c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])), df.columns[0])
    dados = df.set_index(eixo).select_dtypes("number")
    if dados.empty:
        return
    if tipo == "linha":
        st.line_chart(dados)
    else:
        st.bar_chart(dados)


def _mostrar(item: dict) -> None:
    with st.chat_message("user"):
        st.markdown(item["pergunta"])
    with st.chat_message("assistant"):
        r: nucleo.Resposta = item["resposta"]
        if r.tipo == "cota":
            st.warning(r.texto)
        elif r.tipo in ("erro", "recusado"):
            st.error(r.texto)
        elif r.tipo == "fora_do_escopo":
            st.info(f"Essa pergunta está fora do que a base tem: {r.texto}")
        elif r.confirmada or r.tipo == "vazio":
            st.markdown(r.texto)
        else:
            st.warning(r.texto)
        if r.linhas:
            df = _numerico(pd.DataFrame(r.linhas, columns=r.colunas))
            _grafico(df, r.grafico)
            st.dataframe(df, hide_index=True)
        if r.sql:
            with st.expander("SQL gerado"):
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


def _rodape() -> None:
    try:
        resumo = banco.ler_atualizacao(_conexao())
    except Exception:  # noqa: BLE001
        resumo = None
    partes = [resumo, "Base pública Olist, pedidos de set/2016 a out/2018",
              "As perguntas não são gravadas"]
    st.caption(" · ".join(p for p in partes if p))


st.set_page_config(page_title="Pergunte aos dados | Olist", page_icon="🔎", layout="wide")
_carregar_segredos()
for chave, inicial in (("historico", []), ("conversa", []), ("perguntas_feitas", 0)):
    st.session_state.setdefault(chave, inicial)

st.title("Pergunte aos dados do e-commerce")
st.info("Escreva uma pergunta de negócio em português. Ela vira uma consulta SQL nas tabelas "
        "do projeto, e cada resposta mostra a tabela e o SQL gerado para você conferir. "
        "Se um número da frase não bater com o resultado, a frase é descartada.")

clicada = None
for coluna, exemplo in zip(st.columns(len(EXEMPLOS)), EXEMPLOS):
    if coluna.button(exemplo, use_container_width=True):
        clicada = exemplo

pergunta = st.chat_input("Ex.: qual UF teve mais pedidos em 2018?") or clicada
if pergunta:
    _processar(pergunta.strip())

for item in st.session_state.conversa:
    _mostrar(item)

_rodape()
