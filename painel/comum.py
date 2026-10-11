"""Pecas comuns as paginas do painel: cabecalho, filtros e carga das consultas.

Cada visual carrega separado: uma consulta que falha mostra aviso so naquele
visual; banco dormindo (Neon) vira um aviso unico no topo com "Tentar de novo".
"""
from __future__ import annotations

from dataclasses import replace
from html import escape

import pandas as pd
import streamlit as st

from agente import banco
from painel import consultas
from painel.filtros import MAXIMO, MINIMO, REGIOES, Filtros, da_selecao, da_url, mes_referencia, para_url

REPO = "https://github.com/gustavohenriqq/pipeline-olist"
ICONE = ('<svg width="{t}" height="{t}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.2" stroke-linecap="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>')
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")

_aviso = None  # espaco do aviso de banco dormindo, criado pelo cabecalho a cada execucao
_acordando_mostrado = False
_lateral = None  # coluna do agente, quando aberta (criada por corpo())


def mes_extenso(ano_mes: str) -> str:
    ano, mes = ano_mes.split("-")
    return f"{MESES[int(mes) - 1]}/{ano}"


def _alternar_agente() -> None:
    st.session_state.agente_aberto = not st.session_state.get("agente_aberto", False)


def cabecalho(titulo: str, subtitulo: str, pagina: str) -> None:
    global _aviso, _acordando_mostrado
    st.session_state.pagina_atual = pagina
    esquerda, direita = st.columns([5, 1.4], vertical_alignment="center")
    esquerda.markdown(f'<div class="cabecalho"><h1>{escape(titulo)}</h1><p>{escape(subtitulo)}</p></div>',
                      unsafe_allow_html=True)
    aberto = st.session_state.get("agente_aberto", False)
    direita.button("Fechar o agente" if aberto else "Tire sua dúvida", key="abrir_agente",
                   icon=":material/close:" if aberto else ":material/forum:", type="primary",
                   on_click=_alternar_agente, width="stretch")
    _aviso, _acordando_mostrado = st.empty(), False


def corpo():
    """Area do painel: a pagina inteira, ou a coluna da esquerda quando o agente esta aberto."""
    global _lateral
    if st.session_state.get("agente_aberto"):
        esquerda, _lateral = st.columns([3, 1.35], gap="large")
        return esquerda
    _lateral = None
    return st.container()


def coluna_lateral():
    return _lateral


def filtros_da_pagina(regiao: bool) -> Filtros:
    """Periodo (todas as paginas) e regiao (so a visao executiva); guarda no estado e na URL."""
    atual = st.session_state.get("filtros") or da_url(st.query_params)
    colunas = st.columns([2.2, 1.6, 2.4] if regiao else [2.2, 4], vertical_alignment="bottom")
    periodo = colunas[0].date_input("Período", value=(atual.inicio, atual.fim), min_value=MINIMO,
                                    max_value=MAXIMO, format="DD/MM/YYYY", key="periodo")
    novo = da_selecao(periodo, atual)
    if regiao:
        opcoes = ["Todas", *REGIOES]
        escolha = colunas[1].selectbox("Região do cliente", opcoes,
                                       index=opcoes.index(atual.regiao) if atual.regiao else 0, key="regiao")
        novo = replace(novo, regiao=None if escolha == "Todas" else escolha)
    colunas[-1].markdown(f'<div class="bloco-sub" style="text-align:right">'
                         f"{mes_extenso(mes_referencia(novo))} contra o mês anterior</div>",
                         unsafe_allow_html=True)
    st.session_state.filtros = novo
    params = para_url(novo)
    for chave in ("inicio", "fim", "regiao"):
        if chave in params:
            st.query_params[chave] = params[chave]
        elif chave in st.query_params:
            del st.query_params[chave]
    return novo


@st.cache_data(ttl=3600, show_spinner=False)
def _rodar(nome: str, f: Filtros) -> pd.DataFrame:
    """Uma conexao por consulta (o Neon dorme); falha levanta e nao entra no cache."""
    try:
        conexao = banco.abrir_conexao()
    except Exception as erro:  # noqa: BLE001
        raise banco.BancoIndisponivel(str(erro)) from None
    try:
        return getattr(consultas, nome)(conexao, f)
    finally:
        conexao.close()


def _avisar_acordando() -> None:
    global _acordando_mostrado
    if _acordando_mostrado or _aviso is None:
        return
    _acordando_mostrado = True
    with _aviso.container():
        st.warning("O banco está acordando (ele dorme quando ninguém usa). Leva alguns segundos.")
        st.button("Tentar de novo", key="tentar_de_novo", icon=":material/refresh:")


def carregar(funcao, f: Filtros) -> pd.DataFrame | None:
    try:
        return _rodar(funcao.__name__, f)
    except banco.BancoIndisponivel:
        _avisar_acordando()
    except Exception:  # noqa: BLE001 (um visual com erro nao derruba a pagina)
        st.warning("Não consegui carregar este visual agora.")
    return None


def bloco(titulo: str, subtitulo: str = "") -> None:
    sub = f'<div class="bloco-sub">{escape(subtitulo)}</div>' if subtitulo else ""
    st.markdown(f'<div class="bloco-titulo">{escape(titulo)}</div>{sub}', unsafe_allow_html=True)


def sem_dados() -> None:
    st.markdown('<div class="bloco-sub">Sem pedidos neste período.</div>', unsafe_allow_html=True)


def sem_anterior(cartoes: dict, anterior) -> bool:
    """Ha dados no periodo, mas nao no mes anterior ao de referencia (ex.: comeca em set/2016)."""
    return bool(cartoes) and (anterior is None or pd.isna(anterior))


def linha_unica(df: pd.DataFrame | None) -> dict:
    """Primeira linha dos cartoes, ou {} quando a consulta nao trouxe nada."""
    return {} if df is None or df.empty else df.iloc[0].to_dict()
