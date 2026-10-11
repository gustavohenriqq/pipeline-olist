"""Visao executiva: receita, volume, prazo e satisfacao (pagina 1 do Power BI)."""
from __future__ import annotations

import streamlit as st

from agente.apresentacao import tabela_html
from agente.tema import PALETAS
from painel import consultas
from painel.cartoes import cartao, linha_de_cartoes, valor_br
from painel.comum import (bloco, cabecalho, carregar, corpo, filtros_da_pagina, linha_unica, sem_anterior,
                          sem_dados)
from painel.consultas import delta
from painel.graficos import receita_com_ano_anterior
from painel.lateral import coluna_do_agente

TITULO = "Visão executiva"


def _cartoes(c: dict) -> str:
    def destaque(chave: str, taxa: bool = False) -> dict:
        ref, ant = c.get(f"{chave}_ref"), c.get(f"{chave}_ant")
        return {"variacao": delta(ref, ant, taxa=taxa), "taxa": taxa, "sem_anterior": sem_anterior(c, ant)}
    return linha_de_cartoes([
        cartao("Receita", valor_br(c.get("receita"), "moeda_compacta"), "payments", "menta", **destaque("receita")),
        cartao("Pedidos", valor_br(c.get("pedidos"), "inteiro"), "receipt_long", "azul", **destaque("pedidos")),
        cartao("Ticket médio", valor_br(c.get("ticket_medio"), "moeda"), "sell", "violeta", **destaque("ticket")),
        cartao("% no prazo", valor_br(c.get("pct_no_prazo"), "pct"), "local_shipping", "ambar",
               **destaque("pct", taxa=True)),
        cartao("Nota média", valor_br(c.get("nota_media"), "nota"), "star", "menta", **destaque("nota")),
    ])


def pagina() -> None:
    cabecalho(TITULO, "Receita, volume, prazo e satisfação. Período padrão jan/2017 a ago/2018.", TITULO)
    with corpo():
        f = filtros_da_pagina(regiao=True)
        paleta = PALETAS[st.session_state.tema]

        cartoes = carregar(consultas.cartoes_executivo, f)
        if cartoes is not None:
            st.markdown(_cartoes(linha_unica(cartoes)), unsafe_allow_html=True)

        esquerda, direita = st.columns([1.5, 1], gap="large")
        with esquerda:
            bloco("Receita por mês e no mesmo mês do ano anterior", "Área: receita do mês. Tracejado: ano anterior.")
            receita = carregar(consultas.receita_mensal, f)
            if receita is not None:
                if receita.empty:
                    sem_dados()
                else:
                    st.altair_chart(receita_com_ano_anterior(receita, paleta), width="stretch", theme=None)
        with direita:
            bloco("Placar mensal", "Variação contra o mês anterior.")
            placar = carregar(consultas.placar_mensal, f)
            if placar is not None:
                if placar.empty:
                    sem_dados()
                else:
                    st.markdown(tabela_html(placar), unsafe_allow_html=True)
    coluna_do_agente(TITULO, f)
