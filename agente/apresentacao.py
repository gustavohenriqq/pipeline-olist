"""Apresentacao da resposta no app: texto, nomes e formatos de coluna, grafico.

Separado do app para ser testado sem rodar o Streamlit.
"""
from __future__ import annotations

import altair as alt
import pandas as pd

from agente.grafico import COLUNAS_DE_TEMPO

AZUL = "#0F52BA"
ROTULOS = {"ano_mes": "Mês", "mes": "Mês", "ano": "Ano", "uf": "UF", "trimestre": "Trimestre",
           "data": "Data"}


def escapar_markdown(texto: str) -> str:
    """Dois "R$" na mesma frase viram formula no markdown do Streamlit; escapa o cifrao."""
    return texto.replace("$", "\\$")


def rotulo_coluna(nome: str) -> str:
    if nome in ROTULOS:
        return ROTULOS[nome]
    texto = nome.replace("_", " ").strip()
    return texto[:1].upper() + texto[1:]


def formato_coluna(nome: str, serie: pd.Series) -> str | None:
    """Formato de numero na tabela: ano e mes sem milhar; o resto no formato do navegador."""
    if not pd.api.types.is_numeric_dtype(serie):
        return None
    if nome.lower() in COLUNAS_DE_TEMPO or nome.lower() == "dia":
        return "plain"
    return "localized"


def _eixo_e_medidas(df: pd.DataFrame) -> tuple[str, list[str]]:
    eixo = next((c for c in df.columns
                 if str(c).lower() in COLUNAS_DE_TEMPO or not pd.api.types.is_numeric_dtype(df[c])),
                df.columns[0])
    medidas = [c for c in df.columns if c != eixo and pd.api.types.is_numeric_dtype(df[c])]
    return eixo, medidas


def grafico(df: pd.DataFrame, tipo: str) -> alt.Chart:
    """Barras ou linha, eixo do valor compacto (2M, 4M) e sempre a partir do zero."""
    eixo, medidas = _eixo_e_medidas(df)
    dados = df[[eixo, *medidas]].copy()
    dados[eixo] = dados[eixo].astype(str)
    x = alt.X(f"{eixo}:N", sort=None, title=rotulo_coluna(eixo), axis=alt.Axis(labelAngle=0))
    eixo_y = alt.Axis(format="~s")
    escala = alt.Scale(zero=True)
    if len(medidas) == 1:
        y = alt.Y(f"{medidas[0]}:Q", title=rotulo_coluna(medidas[0]), axis=eixo_y, scale=escala)
        base = alt.Chart(dados).encode(x=x, y=y, tooltip=[eixo, medidas[0]])
        marca = base.mark_bar(color=AZUL) if tipo == "barras" else base.mark_line(color=AZUL, point=True)
        return marca.properties(height=320)
    longo = dados.melt(id_vars=[eixo], value_vars=medidas, var_name="serie", value_name="valor")
    longo["serie"] = longo["serie"].map(rotulo_coluna)
    y = alt.Y("valor:Q", title=None, axis=eixo_y, scale=escala)
    base = alt.Chart(longo).encode(x=x, y=y, color=alt.Color("serie:N", title=None),
                                   tooltip=[eixo, "serie", "valor"])
    marca = base.mark_bar() if tipo == "barras" else base.mark_line(point=True)
    return marca.properties(height=320)
