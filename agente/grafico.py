"""Regra do grafico: decidida pela forma do resultado, nao pelo modelo.

Serie no tempo vira linha; categoria com numero e poucas linhas vira barras.
O palpite do modelo so desempata (serie que o usuario quer ver em barras).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pandas as pd

COLUNAS_DE_TEMPO = {"ano_mes", "mes", "data", "ano", "trimestre"}
MAX_BARRAS = 30


def _numerica(serie: pd.Series) -> bool:
    if pd.api.types.is_bool_dtype(serie):
        return False
    if pd.api.types.is_numeric_dtype(serie):
        return True
    validos = serie.dropna()
    return len(validos) > 0 and all(
        isinstance(v, (int, float, Decimal)) and not isinstance(v, bool) for v in validos
    )


def _de_tempo(nome: str, serie: pd.Series) -> bool:
    if nome.lower() in COLUNAS_DE_TEMPO or pd.api.types.is_datetime64_any_dtype(serie):
        return True
    validos = serie.dropna()
    return len(validos) > 0 and all(isinstance(v, (date, datetime)) for v in validos)


def escolher_grafico(df: pd.DataFrame, pedido: bool, palpite: str | None) -> str | None:
    """Devolve "linha", "barras" ou None."""
    if len(df) < 2:
        return None
    numericas = [c for c in df.columns if _numerica(df[c])]
    tempo = [c for c in df.columns if _de_tempo(str(c), df[c])]
    categorias = [c for c in df.columns if c not in numericas and c not in tempo]
    medidas = [c for c in numericas if c not in tempo]
    if not medidas:
        return None
    if tempo:
        return "barras" if palpite == "barras" else "linha"
    if categorias and (len(df) <= MAX_BARRAS or pedido):
        return "barras"
    return None
