"""Coluna "Tire sua duvida": o agente ao lado do painel, com o contexto da tela.

A conversa e a mesma da pagina "Pergunte aos dados" (estado da sessao); aqui ela
aparece compacta (sem grafico, tabela curta) e cada pergunta leva a pagina e os
filtros como contexto, para "e por UF?" ja vir no recorte da tela.
"""
from __future__ import annotations

import streamlit as st

from painel.comum import coluna_lateral
from painel.filtros import Filtros, contexto


def coluna_do_agente(pagina: str, f: Filtros) -> None:
    coluna = coluna_lateral()
    if coluna is None:
        return
    from painel.paginas.pergunte import mostrar, processar  # evita import circular

    with coluna:
        st.markdown('<div class="bloco-titulo">Tire sua dúvida</div>'
                    '<div class="bloco-sub">Pergunte sobre o que está na tela. '
                    "A resposta mostra a tabela e o SQL.</div>", unsafe_allow_html=True)
        pergunta = st.chat_input("Ex.: e por UF?", key="pergunta_lateral")
        if pergunta:
            processar(pergunta.strip(), contexto=contexto(pagina, f))
        for item in reversed(st.session_state.conversa[-6:]):
            mostrar(item, compacto=True)
