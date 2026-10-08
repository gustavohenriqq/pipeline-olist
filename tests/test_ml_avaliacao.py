"""Custo, escolha de limiar, metricas e PSI em dados sinteticos."""
import numpy as np
import pandas as pd
import pytest

from ml.avaliacao import custo, escolher_limiar, metricas, psi


def test_custo_conta_alertas_e_atrasos_perdidos():
    y = np.array([1, 0, 1, 0])
    alerta = np.array([1, 1, 0, 0], dtype=bool)
    assert custo(y, alerta, 15, 60) == pytest.approx(90.0)


def test_limiar_separacao_perfeita():
    y = np.array([0, 0, 1, 1])
    prob = np.array([0.1, 0.2, 0.8, 0.9])
    assert escolher_limiar(y, prob, 15, 60) == pytest.approx(0.80)


def test_limiar_quando_acao_e_cara_nao_alerta():
    y = np.array([0, 1])
    prob = np.array([0.3, 0.6])
    assert escolher_limiar(y, prob, 100, 1) == pytest.approx(0.99)


def test_metricas_sem_positivos_nao_quebra():
    y = np.zeros(10, dtype=int)
    prob = np.linspace(0.05, 0.5, 10)
    m = metricas(y, prob, 0.3, 15, 60)
    assert m["pr_auc"] is None
    assert m["roc_auc"] is None
    assert m["custo_nunca"] == 0


def test_psi_mesma_distribuicao_proximo_de_zero():
    rng = np.random.default_rng(42)
    a = pd.Series(rng.normal(0, 1, 5000))
    b = pd.Series(rng.normal(0, 1, 5000))
    assert psi(a, b) < 0.02


def test_psi_distribuicao_deslocada_acima_de_02():
    rng = np.random.default_rng(42)
    a = pd.Series(rng.normal(0, 1, 5000))
    b = pd.Series(rng.normal(1, 1, 5000))
    assert psi(a, b) > 0.2


def test_psi_categorica():
    a = pd.Series(["a"] * 50 + ["b"] * 50)
    b = pd.Series(["a"] * 90 + ["b"] * 10)
    assert psi(a, b) > 0.2
