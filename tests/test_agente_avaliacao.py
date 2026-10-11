"""Comparacao de resultados da avaliacao: mesmos numeros, sem olhar nome nem ordem."""
from decimal import Decimal

from agente.avaliacao.avaliar import mesmo_resultado


def test_colunas_em_outra_ordem():
    assert mesmo_resultado([("SP", 10)], [(10, "SP")])


def test_linhas_em_outra_ordem():
    assert mesmo_resultado([("SP", 10), ("RJ", 5)], [("RJ", 5), ("SP", 10)])


def test_decimal_contra_float_arredondado():
    assert mesmo_resultado([(Decimal("0.93226"),)], [(0.932263,)])


def test_numero_diferente_na_terceira_casa_de_um_total():
    assert not mesmo_resultado([(Decimal("15843553.24"),)], [(15843553.25,)])


def test_quantidade_de_linhas_diferente():
    assert not mesmo_resultado([("SP", 10)], [("SP", 10), ("RJ", 5)])


def test_texto_sem_acento_e_sem_caixa():
    assert mesmo_resultado([("São Paulo", 1)], [("sao paulo", 1)])
