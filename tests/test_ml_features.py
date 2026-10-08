"""Lista permitida de features e pre-processamento dos dois modelos."""
import numpy as np
import pandas as pd
import pytest

from ml.features import (
    CATEGORICAS, NUMERICAS, PERMITIDAS, PROIBIDAS,
    matriz, modelo_logistica, modelo_principal,
)


def _sintetico(n=200, seed=42):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.normal(10, 3, n) for c in NUMERICAS})
    for c in CATEGORICAS:
        df[c] = rng.choice(["SP", "RJ", "MG"], n)
    df["atrasou"] = (df["prazo_prometido_dias"] < 9).astype(int)
    df.loc[:4, "atrasou"] = [0, 1, 0, 1, 0]
    return df


def test_permitidas_e_proibidas_nao_se_cruzam():
    assert set(PERMITIDAS) & set(PROIBIDAS) == set()


def test_matriz_descarta_colunas_extras():
    df = _sintetico()
    df["atraso_dias"] = 3.0
    df["pedido_sk"] = "x"
    assert list(matriz(df).columns) == list(PERMITIDAS)


def test_matriz_acusa_coluna_faltando():
    df = _sintetico().drop(columns=["distancia_km"])
    with pytest.raises(ValueError, match="distancia_km"):
        matriz(df)


def test_modelos_aceitam_categoria_nova_e_nulos():
    treino = _sintetico()
    novos = _sintetico(n=5, seed=7)
    novos["cliente_uf"] = "ZZ"
    novos["distancia_km"] = np.nan
    novos.loc[0, "categoria_grupo"] = None
    for modelo in (modelo_logistica(), modelo_principal()):
        modelo.fit(matriz(treino), treino["atrasou"])
        prob = modelo.predict_proba(matriz(novos))[:, 1]
        assert len(prob) == 5
        assert ((prob >= 0) & (prob <= 1)).all()
