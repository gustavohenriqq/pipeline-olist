"""Apresentacao da resposta no app: texto, nomes e formatos de coluna, grafico.

Separado do app para ser testado sem rodar o Streamlit.
"""
from __future__ import annotations

from numbers import Number
from typing import Callable

import altair as alt
import pandas as pd

from agente.grafico import COLUNAS_DE_TEMPO

AZUL = "#4F8DF7"  # mesmo azul do tema escuro (.streamlit/config.toml)
# Eixo do valor como no texto da resposta: 8 mi, 500 mil, 0,08.
ROTULO_COMPACTO = (
    "replace(abs(datum.value) >= 1e9 ? format(datum.value / 1e9, '~g') + ' bi'"
    " : abs(datum.value) >= 1e6 ? format(datum.value / 1e6, '~g') + ' mi'"
    " : abs(datum.value) >= 1e3 ? format(datum.value / 1e3, '~g') + ' mil'"
    " : format(datum.value, '~g'), '.', ',')"
)
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


def _so_numeros(serie: pd.Series) -> bool:
    valores = serie.dropna()
    return bool(len(valores)) and all(isinstance(v, Number) and not isinstance(v, bool) for v in valores)


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Decimal do banco vira float; coluna so de inteiros (ano, contagem) vira inteiro.

    O Postgres devolve ano e contagens como numeric as vezes, e o float resultante
    aparecia como 2016.0 no eixo e 2017.0000000000002 na tabela.
    """
    saida = df.copy()
    for coluna in saida.columns:
        serie = saida[coluna]
        if pd.api.types.is_bool_dtype(serie) or not _so_numeros(serie):
            continue
        serie = serie.astype(float)
        if ((serie - serie.round()).abs().dropna() < 1e-6).all():
            serie = serie.round().astype("Int64")
        saida[coluna] = serie
    return saida


def numero_br(valor: float, casas: int, milhar: bool = True) -> str:
    if pd.isna(valor):
        return ""
    texto = f"{valor:,.{casas}f}" if milhar else f"{valor:.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def formatadores(df: pd.DataFrame) -> dict[str, Callable[[float], str]]:
    """Formato brasileiro fixo por coluna, sem depender do idioma do navegador.

    Ano e mes sem milhar; contagem com milhar; valor com 2 casas; taxa (tudo abaixo de 1) com 4.
    """
    saida = {}
    for coluna in df.columns:
        serie = df[coluna]
        if pd.api.types.is_bool_dtype(serie) or not pd.api.types.is_numeric_dtype(serie):
            continue
        if str(coluna).lower() in COLUNAS_DE_TEMPO or str(coluna).lower() == "dia":
            casas, milhar = 0, False
        elif pd.api.types.is_integer_dtype(serie):
            casas, milhar = 0, True
        else:
            valores = serie.dropna().abs()
            casas, milhar = (4 if len(valores) and valores.max() < 1 else 2), True
        saida[coluna] = lambda v, c=casas, m=milhar: numero_br(v, c, m)
    return saida


def _eixo_e_medidas(df: pd.DataFrame) -> tuple[str, list[str]]:
    eixo = next((c for c in df.columns
                 if str(c).lower() in COLUNAS_DE_TEMPO or not pd.api.types.is_numeric_dtype(df[c])),
                df.columns[0])
    medidas = [c for c in df.columns if c != eixo and pd.api.types.is_numeric_dtype(df[c])]
    return eixo, medidas


def grafico(df: pd.DataFrame, tipo: str) -> alt.Chart:
    """Barras ou linha, eixo do valor compacto (2 mi, 4 mi) e sempre a partir do zero."""
    eixo, medidas = _eixo_e_medidas(df)
    dados = df[[eixo, *medidas]].copy()
    dados[eixo] = dados[eixo].astype(str)
    x = alt.X(f"{eixo}:N", sort=None, title=rotulo_coluna(eixo), axis=alt.Axis(labelAngle=0))
    eixo_y = alt.Axis(labelExpr=ROTULO_COMPACTO)
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
