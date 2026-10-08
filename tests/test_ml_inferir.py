"""Inferencia: modelo ausente, conjunto de cada pedido e montagem da saida."""
import numpy as np
import pandas as pd
import pytest

from ml.inferir import COLUNAS_SAIDA, atribuir_conjunto, carregar_modelo, montar_saida


def test_carregar_modelo_ausente_explica_o_que_fazer(tmp_path):
    with pytest.raises(FileNotFoundError, match="python -m ml.treinar"):
        carregar_modelo(tmp_path / "nao_existe.joblib")


def test_atribuir_conjunto():
    df = pd.DataFrame({
        "purchased_at": pd.to_datetime(["2017-06-10", "2018-02-10", "2018-07-10", "2018-07-11"]),
        "atrasou": pd.array([0, 1, 0, pd.NA], dtype="Int64"),
    })
    assert list(atribuir_conjunto(df)) == ["treino", "validacao", "teste", "em_andamento"]


def test_montar_saida_alerta_no_limiar():
    df = pd.DataFrame({
        "pedido_sk": ["a", "b", "c"],
        "purchased_at": pd.to_datetime(["2018-06-01", "2018-06-02", "2018-06-03"]),
        "atrasou": pd.array([0, 1, 0], dtype="Int64"),
    })
    gerado_em = pd.Timestamp("2026-10-08 12:00", tz="UTC")
    saida = montar_saida(df, np.array([0.19, 0.20, 0.21]), 0.20, "v1", gerado_em)
    assert list(saida.columns) == [
        "pedido_sk", "prob_atraso", "alerta", "conjunto", "limiar", "modelo_versao", "gerado_em",
    ]
    assert list(saida.columns) == list(COLUNAS_SAIDA)
    assert list(saida["alerta"]) == [False, True, True]
    assert list(saida["conjunto"]) == ["teste"] * 3
