"""Entrega e risco: atraso por regiao e UF, e pedidos em andamento com maior risco previsto."""
from __future__ import annotations

from dataclasses import replace

import pandas as pd
import streamlit as st

from agente.apresentacao import tabela_html
from agente.tema import PALETAS
from painel import consultas
from painel.cartoes import cartao, linha_de_cartoes, valor_br
from painel.comum import (bloco, cabecalho, carregar, corpo, filtros_da_pagina, linha_unica, rotulo_do_destaque,
                          sem_anterior, sem_dados)
from painel.consultas import delta
from painel.graficos import barras_regiao, excesso_divergente
from painel.lateral import coluna_do_agente

TITULO = "Entrega e risco"


def _risco(linha) -> str:
    # Mesmos cortes da medida de cor da probabilidade no Power BI.
    prob = linha.get("prob_atraso")
    return "risco-alto" if prob >= 0.4 else "risco-medio" if prob >= 0.3 else ""


def pagina() -> None:
    cabecalho(TITULO, "Atraso por região e UF, e pedidos em andamento com maior risco previsto.", TITULO)
    with corpo():
        f = filtros_da_pagina(regiao=False)
        paleta = PALETAS[st.session_state.tema]

        cartoes = carregar(consultas.cartoes_entrega, f)
        if cartoes is not None:
            c = linha_unica(cartoes)
            rotulo_do_destaque(c)
            ant, taxa = c.get("taxa_ant"), c.get("taxa_atraso")
            # Periodo com pedidos e nenhum entregue: taxa "sem dados" e sem destaque (como o Power BI).
            tem_taxa = taxa is not None and not pd.isna(taxa)
            st.markdown(linha_de_cartoes([
                cartao("Taxa de atraso", valor_br(taxa, "pct"), "schedule", "ambar",
                       delta(c.get("taxa_ref"), ant, taxa=True), taxa=True, piora_quando_sobe=True,
                       sem_anterior=tem_taxa and sem_anterior(c, ant)),
                cartao("Pedidos em alerta", valor_br(c.get("pedidos_alerta"), "inteiro"), "notifications_active",
                       "violeta"),
                cartao("Receita em risco", valor_br(c.get("receita_risco"), "moeda_compacta"), "warning", "azul"),
            ]), unsafe_allow_html=True)

        if st.session_state.get("agente_aberto"):
            # Com o agente ao lado, tres colunas ficam estreitas: graficos lado a lado, tabela embaixo.
            regiao, uf = st.columns(2, gap="large")
            risco = st.container()
        else:
            regiao, uf, risco = st.columns([1, 1, 1.7], gap="large")
        with regiao:
            bloco("Taxa de atraso por região", "Linha tracejada: taxa nacional.")
            df = carregar(consultas.taxa_por_regiao, f)
            if df is not None:
                if df.empty:
                    sem_dados()
                else:
                    st.altair_chart(barras_regiao(df, paleta), width="stretch", theme=None)
        with uf:
            bloco("Atraso em excesso por UF", "Vermelho: acima do esperado pela taxa nacional.")
            df = carregar(consultas.excesso_por_uf, f)
            if df is not None:
                if df.empty:
                    sem_dados()
                else:
                    st.altair_chart(excesso_divergente(df, paleta).properties(height=max(320, 18 * len(df))),
                                    width="stretch", theme=None)
        with risco:
            bloco("Pedidos em andamento por probabilidade de atraso", "Os 50 de maior risco comprados no período.")
            df = carregar(consultas.pedidos_em_risco, f)
            if df is not None:
                if df.empty:
                    sem_dados()
                else:
                    st.markdown(tabela_html(df, classe_linha=_risco), unsafe_allow_html=True)
    coluna_do_agente(TITULO, replace(f, regiao=None))
