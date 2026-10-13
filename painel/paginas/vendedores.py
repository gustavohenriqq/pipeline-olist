"""Vendedores: receita de itens por grupo de categoria e por vendedor (grao de item)."""
from __future__ import annotations

from dataclasses import replace

import streamlit as st

from agente.apresentacao import tabela_html
from agente.tema import PALETAS
from painel import consultas
from painel.cartoes import cartao, linha_de_cartoes, valor_br
from painel.comum import (bloco, cabecalho, carregar, corpo, filtros_da_pagina, linha_unica, rotulo_do_destaque,
                          sem_anterior, sem_dados)
from painel.consultas import delta
from painel.graficos import barras_horizontais
from painel.lateral import coluna_do_agente

TITULO = "Vendedores"


def pagina() -> None:
    cabecalho(TITULO, "No grão de item: exato para cada vendedor.", TITULO)
    with corpo():
        f = filtros_da_pagina(regiao=False)
        paleta = PALETAS[st.session_state.tema]

        cartoes = carregar(consultas.cartoes_vendedores, f)
        if cartoes is not None:
            c = linha_unica(cartoes)
            rotulo_do_destaque(c)
            ant = c.get("receita_ant")
            st.markdown(linha_de_cartoes([
                cartao("Receita de itens", valor_br(c.get("receita_itens"), "moeda_compacta"), "payments", "menta",
                       delta(c.get("receita_ref"), ant, taxa=False), sem_anterior=sem_anterior(c, ant)),
                cartao("Itens", valor_br(c.get("itens"), "inteiro"), "inventory_2", "azul"),
                cartao("Taxa de atraso dos itens", valor_br(c.get("taxa_atraso_itens"), "pct"), "schedule", "ambar"),
            ]), unsafe_allow_html=True)

        grupos, lista = st.columns([1, 1.2], gap="large")
        with grupos:
            bloco("Receita de itens por grupo de categoria")
            df = carregar(consultas.receita_por_grupo, f)
            if df is not None:
                if df.empty:
                    sem_dados()
                else:
                    grafico = barras_horizontais(df, "categoria_grupo", "receita_itens", paleta)
                    st.altair_chart(grafico.properties(height=max(320, 26 * len(df))), width="stretch",
                                    theme=None)
        with lista:
            bloco("Receita e atraso por vendedor", "Os 50 de maior receita de itens no período.")
            df = carregar(consultas.vendedores, f)
            if df is not None:
                if df.empty:
                    sem_dados()
                else:
                    st.markdown(tabela_html(df), unsafe_allow_html=True)
    coluna_do_agente(TITULO, replace(f, regiao=None))
