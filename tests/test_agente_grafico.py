"""Regra do grafico: linha para serie no tempo, barras para ranking curto."""
from datetime import date
from decimal import Decimal

import pandas as pd

from agente.grafico import escolher_grafico


def _serie_mensal():
    return pd.DataFrame({
        "ano_mes": [f"2017-{m:02d}" for m in range(1, 13)] + [f"2018-{m:02d}" for m in range(1, 9)],
        "receita": [Decimal("1000.50")] * 20,
    })


def test_serie_mensal_vira_linha():
    assert escolher_grafico(_serie_mensal(), pedido=False, palpite=None) == "linha"


def test_coluna_de_data_vira_linha():
    df = pd.DataFrame({"data": [date(2018, 1, d) for d in range(1, 6)], "pedidos": [1, 2, 3, 4, 5]})
    assert escolher_grafico(df, pedido=False, palpite=None) == "linha"


def test_ranking_curto_vira_barras():
    df = pd.DataFrame({"uf": ["SP", "RJ", "MG", "BA", "PR"], "pedidos": [5, 4, 3, 2, 1]})
    assert escolher_grafico(df, pedido=False, palpite=None) == "barras"


def test_muitas_categorias_sem_pedido_fica_sem_grafico():
    df = pd.DataFrame({"cidade": [f"c{i}" for i in range(40)], "pedidos": range(40)})
    assert escolher_grafico(df, pedido=False, palpite=None) is None


def test_muitas_categorias_com_pedido_vira_barras():
    df = pd.DataFrame({"cidade": [f"c{i}" for i in range(40)], "pedidos": range(40)})
    assert escolher_grafico(df, pedido=True, palpite=None) == "barras"


def test_valor_unico_fica_sem_grafico():
    assert escolher_grafico(pd.DataFrame({"pedidos": [99441]}), pedido=True, palpite=None) is None


def test_so_texto_fica_sem_grafico():
    df = pd.DataFrame({"uf": ["SP", "RJ"], "regiao": ["Sudeste", "Sudeste"]})
    assert escolher_grafico(df, pedido=True, palpite=None) is None


def test_palpite_de_barras_desempata_serie():
    assert escolher_grafico(_serie_mensal(), pedido=False, palpite="barras") == "barras"
