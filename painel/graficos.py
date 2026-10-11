"""Graficos do painel (Altair), nas cores da paleta do tema."""
from __future__ import annotations

import altair as alt
import pandas as pd

from agente.apresentacao import ROTULO_COMPACTO, com_cores

_EIXO_COMPACTO = alt.Axis(labelExpr=ROTULO_COMPACTO, title=None)
_EIXO_PCT = alt.Axis(format=".0%", title=None)


def receita_com_ano_anterior(df: pd.DataFrame, paleta: dict) -> alt.LayerChart:
    """Receita do mes em area com degrade e o mesmo mes do ano anterior em linha tracejada."""
    base = alt.Chart(df).encode(x=alt.X("ano_mes:N", title=None, axis=alt.Axis(labelAngle=-45)))
    degrade = alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0, stops=[
        alt.GradientStop(color="transparent", offset=0),
        alt.GradientStop(color=paleta["destaque"], offset=1),
    ])
    area = base.mark_area(line={"color": paleta["destaque"], "strokeWidth": 2.5}, color=degrade,
                          opacity=0.55, interpolate="monotone").encode(
        y=alt.Y("receita:Q", axis=_EIXO_COMPACTO, scale=alt.Scale(zero=True)),
        tooltip=[alt.Tooltip("ano_mes:N", title="Mês"), alt.Tooltip("receita:Q", title="Receita", format=",.2f")])
    anterior = base.mark_line(color=paleta["azul"], strokeDash=[5, 4], strokeWidth=2,
                              interpolate="monotone").encode(
        y="receita_ano_anterior:Q",
        tooltip=[alt.Tooltip("ano_mes:N", title="Mês"),
                 alt.Tooltip("receita_ano_anterior:Q", title="Ano anterior", format=",.2f")])
    return com_cores(alt.layer(area, anterior), paleta)


def barras_regiao(df: pd.DataFrame, paleta: dict) -> alt.LayerChart:
    """Taxa de atraso por regiao em barras, com a taxa nacional como linha vertical."""
    base = alt.Chart(df)
    barras = base.mark_bar(color=paleta["azul"], cornerRadiusEnd=6).encode(
        y=alt.Y("regiao:N", sort="-x", title=None),
        x=alt.X("taxa_atraso:Q", axis=_EIXO_PCT),
        tooltip=[alt.Tooltip("regiao:N", title="Região"),
                 alt.Tooltip("taxa_atraso:Q", title="Taxa de atraso", format=".1%")])
    nacional = base.mark_rule(color=paleta["vermelho"], strokeDash=[4, 3], strokeWidth=2).encode(
        x="mean(taxa_nacional):Q")
    return com_cores(alt.layer(barras, nacional), paleta)


def excesso_divergente(df: pd.DataFrame, paleta: dict) -> alt.Chart:
    """Atraso em excesso por UF: vermelho acima do esperado pela taxa nacional, menta abaixo."""
    grafico = alt.Chart(df).mark_bar(cornerRadiusEnd=4).encode(
        y=alt.Y("uf:N", sort="-x", title=None),
        x=alt.X("atraso_em_excesso:Q", title=None, axis=alt.Axis(format=",.0f")),
        color=alt.condition(alt.datum.atraso_em_excesso > 0, alt.value(paleta["vermelho"]),
                            alt.value(paleta["destaque"])),
        tooltip=[alt.Tooltip("uf:N", title="UF"),
                 alt.Tooltip("atraso_em_excesso:Q", title="Atraso em excesso", format=",.0f")])
    return com_cores(grafico, paleta)


def barras_horizontais(df: pd.DataFrame, rotulo: str, valor: str, paleta: dict) -> alt.Chart:
    grafico = alt.Chart(df).mark_bar(color=paleta["violeta"], cornerRadiusEnd=6).encode(
        y=alt.Y(f"{rotulo}:N", sort="-x", title=None),
        x=alt.X(f"{valor}:Q", axis=_EIXO_COMPACTO),
        tooltip=[alt.Tooltip(f"{rotulo}:N", title="Grupo"), alt.Tooltip(f"{valor}:Q", title="Receita", format=",.2f")])
    return com_cores(grafico, paleta)
