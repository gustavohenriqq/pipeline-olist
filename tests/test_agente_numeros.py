"""Checagem anti-invencao: todo numero da resposta precisa estar no resultado."""
from datetime import date
from decimal import Decimal

import pytest

from agente.numeros import confere, extrair_numeros


@pytest.mark.parametrize("texto, esperado", [
    ("R$ 1.565.470,97", [1565470.97]),
    ("15,79 mi", [15790000.0]),
    ("R$ 2,3 milhões", [2300000.0]),
    ("8 mil", [8000.0]),
    ("93,2%", [93.2]),
    ("99.441 pedidos", [99441.0]),
])
def test_extrai_numeros_em_formato_brasileiro(texto, esperado):
    assert extrair_numeros(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("texto", ["2018-03", "mar/2018", "em 01/08/2018"])
def test_datas_nao_viram_numero(texto):
    assert extrair_numeros(texto) == []


def test_receita_abreviada_confere():
    assert confere("A receita foi de R$ 15,79 mi.", [Decimal("15786203.57")])


def test_percentual_confere_com_fracao():
    assert confere("93,2% dos pedidos chegaram no prazo", [0.93226])


def test_arredondamento_inteiro_confere():
    assert confere("O RJ teve 659 atrasos a mais que o esperado", [Decimal("658.65")])


def test_numero_inventado_reprova():
    assert not confere("SP lidera com 41 mil pedidos", [Decimal("38720")])


def test_numero_exato_errado_reprova():
    assert not confere("Foram 8.468 pedidos em alerta", [8467])


def test_numeros_da_pergunta_e_do_sql_passam():
    assert confere("Em 2018, as 3 UFs com mais atraso", [12], extras=[2018, 3])


def test_texto_sem_numero_confere():
    assert confere("Nenhum registro encontrado.", [])


def test_none_e_data_no_resultado_sao_ignorados():
    assert confere("Foram 12 pedidos", [None, date(2018, 3, 1), "SP", 12])


def test_negativo_confere():
    assert confere("A receita caiu -5,2% em agosto", [Decimal("-0.0523")])


def test_negativo_inventado_reprova():
    assert not confere("A receita caiu -9,9% em agosto", [Decimal("-0.0523")])
