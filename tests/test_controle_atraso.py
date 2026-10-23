"""Estimador da secao 1.2 de docs/analise-atraso.md (scripts/controle_atraso.py).

O intervalo de confianca do efeito do atraso sai destas funcoes, entao elas
sao conferidas contra contas de resposta conhecida, sem banco.
"""
import numpy as np
import pandas as pd

from scripts.controle_atraso import centrar_por_grupo, ols_cluster, tabela_por_grupo


def test_ols_recupera_coeficientes_sem_ruido():
    rng = np.random.default_rng(0)
    X = np.column_stack([np.ones(200), rng.normal(size=(200, 2))])
    y = X @ np.array([4.0, -1.5, 0.3])
    beta, _ = ols_cluster(X, y, np.arange(200) % 10)
    assert np.allclose(beta, [4.0, -1.5, 0.3])


def test_um_pedido_por_grupo_vira_hc1():
    # Com cada observacao no proprio grupo, CR1 e o HC1 de White: n/(n-k).
    rng = np.random.default_rng(1)
    n = 300
    X = np.column_stack([np.ones(n), rng.normal(size=n)])
    y = X @ np.array([1.0, 2.0]) + rng.normal(size=n) * (1 + np.abs(X[:, 1]))
    beta, ep = ols_cluster(X, y, np.arange(n))
    u = y - X @ beta
    inv = np.linalg.inv(X.T @ X)
    hc1 = n / (n - 2) * inv @ (X.T * u**2) @ X @ inv
    assert np.allclose(ep, np.sqrt(np.diag(hc1)))


def test_within_igual_a_regressao_com_dummy_de_vendedor():
    rng = np.random.default_rng(2)
    vendedor = np.repeat(np.arange(30), 20)
    x = rng.normal(size=600) + vendedor * 0.1
    y = -1.5 * x + vendedor * 0.5 + rng.normal(size=600)
    beta_within, _ = ols_cluster(
        centrar_por_grupo(x[:, None], vendedor), centrar_por_grupo(y, vendedor), vendedor
    )
    dummies = (vendedor[:, None] == np.arange(30)).astype(float)
    beta_lsdv, _ = ols_cluster(np.column_stack([x, dummies]), y, vendedor)
    assert np.isclose(beta_within[0], beta_lsdv[0])


def test_tabela_usa_so_pedidos_avaliados():
    df = pd.DataFrame({
        "grupo": ["A"] * 4,
        "faixa_atraso": ["No prazo", "No prazo", "1 a 7 dias", "8 a 30 dias"],
        "nota": [5.0, None, 2.0, 1.0],
    })
    tab = tabela_por_grupo(df, "grupo")
    assert tab.loc["A", "Pedidos"] == 3
    assert tab.loc["A", "No prazo"] == 5.0
    assert tab.loc["A", "Queda até 8 a 30"] == 4.0
