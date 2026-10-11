"""App publico: painel (3 paginas do Power BI) e o agente, num link so.

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

import streamlit as st  # noqa: E402

from agente import banco  # noqa: E402
from agente.apresentacao import escapar_markdown  # noqa: E402
from agente.tema import css, tema_valido  # noqa: E402
from painel.comum import REPO  # noqa: E402
from painel.filtros import da_url  # noqa: E402

MARCA = str(Path(__file__).resolve().parent / "marca.svg")


def _carregar_segredos() -> None:
    """No Streamlit Cloud os segredos ficam em st.secrets; o resto do codigo le o ambiente."""
    try:
        for chave, valor in st.secrets.items():
            os.environ.setdefault(chave, str(valor))
    except Exception:  # noqa: BLE001 (sem secrets.toml local)
        pass


@st.cache_data(ttl=600, show_spinner=False)
def _resumo_dos_dados() -> str | None:
    # Falha levanta e nao entra no cache: na proxima tela tenta de novo.
    conexao = banco.abrir_conexao()
    try:
        return banco.ler_atualizacao(conexao)
    finally:
        conexao.close()


def _alternar_tema() -> None:
    estado = st.session_state
    estado.tema = "escuro" if estado.tema == "claro" else "claro"
    st.query_params["tema"] = estado.tema


def _nova_conversa() -> None:
    # perguntas_feitas fica: o limite e por sessao, nao por conversa.
    st.session_state.conversa = []
    st.session_state.historico = []


def preparar() -> None:
    """Configuracao, segredos, estado da sessao e tema; roda antes de qualquer pagina."""
    st.set_page_config(page_title="Painel Olist", page_icon="📊", layout="wide",
                       initial_sidebar_state="auto")
    _carregar_segredos()
    estado = st.session_state
    for chave, inicial in (("historico", []), ("conversa", []), ("perguntas_feitas", 0),
                           ("agente_aberto", False)):
        estado.setdefault(chave, inicial)
    estado.setdefault("tema", tema_valido(st.query_params.get("tema")))
    estado.setdefault("filtros", da_url(st.query_params))
    st.html(f"<style>{css(estado.tema)}</style>")


def barra_lateral() -> None:
    with st.sidebar:
        # tema ao lado de "Nova conversa": a barra lateral nao rola com a pagina
        nova, tema = st.columns([1, 0.28], vertical_alignment="center")
        nova.button("Nova conversa", key="nova_conversa", icon=":material/edit_square:",
                    on_click=_nova_conversa, width="stretch")
        escuro = st.session_state.tema == "escuro"
        tema.button("", key="alternar_tema", on_click=_alternar_tema, width="stretch",
                    icon=":material/light_mode:" if escuro else ":material/dark_mode:",
                    help="Tema claro" if escuro else "Tema escuro")
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
            resumo = _resumo_dos_dados()
        except Exception:  # noqa: BLE001
            resumo = None
        partes = [resumo, "Base pública Olist, pedidos de set/2016 a out/2018",
                  "As perguntas não são gravadas"]
        st.caption(" · ".join(p for p in partes if p))


def main() -> None:
    from painel.paginas import entrega, executivo, pergunte, vendedores

    preparar()
    st.logo(MARCA, size="large")
    menu = st.navigation([
        st.Page(executivo.pagina, title="Visão executiva", icon=":material/insights:",
                default=True),
        st.Page(entrega.pagina, title="Entrega e risco", icon=":material/local_shipping:", url_path="entrega"),
        st.Page(vendedores.pagina, title="Vendedores", icon=":material/storefront:", url_path="vendedores"),
        st.Page(pergunte.pagina, title="Pergunte aos dados", icon=":material/forum:", url_path="pergunte"),
    ])
    menu.run()
    barra_lateral()


if __name__ == "__main__":
    main()
