"""Treino de ponta a ponta em dados sinteticos pequenos (teste de fumaca)."""
import json

import numpy as np
import pandas as pd
import pytest

from ml.features import CATEGORICAS, NUMERICAS
from ml.treinar import ajustar_baseline, executar, prever_baseline

GRADE_RAPIDA = [{"learning_rate": 0.1, "max_depth": 3, "min_samples_leaf": 20}]


def test_baseline_uf_desconhecida_usa_taxa_geral():
    treino = pd.DataFrame({
        "cliente_uf": ["SP"] * 10 + ["RJ"] * 10,
        "atrasou": [1] + [0] * 9 + [1, 1] + [0] * 8,
    })
    tabela, geral = ajustar_baseline(treino)
    assert tabela["SP"] == pytest.approx(0.10)
    assert tabela["RJ"] == pytest.approx(0.20)
    assert geral == pytest.approx(0.15)
    prob = prever_baseline(tabela, geral, pd.DataFrame({"cliente_uf": ["SP", "ZZ", None]}))
    assert prob == pytest.approx([0.10, 0.15, 0.15])


def _conjunto(n, inicio, fim, seed, rotulado=True):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.normal(20, 6, n) for c in NUMERICAS})
    for c in CATEGORICAS:
        df[c] = rng.choice(["SP", "RJ", "BA"], n)
    df["pedido_sk"] = [f"p{seed}_{i}" for i in range(n)]
    segundos = rng.integers(0, int((pd.Timestamp(fim) - pd.Timestamp(inicio)).total_seconds()), n)
    df["purchased_at"] = pd.Timestamp(inicio) + pd.to_timedelta(segundos, unit="s")
    # ~10% de atraso, concentrado nos prazos curtos.
    risco = 1 / (1 + np.exp((df["prazo_prometido_dias"] - 12) / 2))
    df["atrasou"] = pd.array((rng.random(n) < risco).astype(int), dtype="Int64")
    if not rotulado:
        df["atrasou"] = pd.array([pd.NA] * n, dtype="Int64")
    return df


def test_executar_fumaca():
    conjuntos = {
        "treino": _conjunto(600, "2017-01-01", "2018-01-01", 1),
        "validacao": _conjunto(300, "2018-01-01", "2018-03-01", 2),
        "teste": _conjunto(300, "2018-05-01", "2018-09-01", 3),
        "em_andamento": _conjunto(50, "2018-06-01", "2018-09-01", 4, rotulado=False),
    }
    todos = pd.concat([conjuntos[k] for k in ("treino", "validacao", "teste")])
    atraso_dias = pd.DataFrame({
        "pedido_sk": todos["pedido_sk"],
        "atraso_dias": np.where(todos["atrasou"] == 1, 5.0, -10.0),
    })

    r = executar(conjuntos, atraso_dias=atraso_dias, grade=GRADE_RAPIDA)

    assert {"limiar", "params", "modelo_final", "relatorio"} <= set(r)
    assert 0.01 <= r["limiar"] <= 0.99
    rel = r["relatorio"]
    for chave in ("validacao", "teste", "sensibilidade", "calibracao", "backtest", "drift", "sanidade", "n", "versao"):
        assert chave in rel
    assert set(rel["teste"]) == {"baseline", "logistica", "principal"}
    assert rel["n"] == {"treino": 600, "validacao": 300, "teste": 300, "em_andamento": 50}
    assert len(rel["backtest"]) >= 1
    assert rel["sanidade"]["roc_auc"] > 0.95
    assert "prazo_prometido_dias" in rel["drift"]["treino_vs_em_andamento"]
    json.dumps(rel)
