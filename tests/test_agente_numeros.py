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


def test_numero_dentro_de_rotulo_do_resultado_confere():
    assert confere("O maior vendedor é Guariba/SP · 4869f7, com R$ 249.640,70.",
                   ["Guariba/SP · 4869f7", Decimal("249640.70")])


def test_numero_de_rotulo_nao_libera_outro_numero():
    assert not confere("Guariba/SP · 4869f7 vendeu 9.999 itens.", ["Guariba/SP · 4869f7", 1156])


def test_decimal_com_ponto_e_lido():
    assert extrair_numeros("A taxa foi 12.5%") == [12.5]
    assert extrair_numeros("nota 4.09") == [4.09]
    assert extrair_numeros("taxa de 0.0812") == [0.0812]
    assert extrair_numeros("1.234 pedidos") == [1234.0]


def test_decimal_com_ponto_inventado_nao_passa():
    assert not confere("A taxa de atraso foi 12.5%.", [Decimal("0.0812")])
    assert confere("A taxa de atraso foi 8.12%.", [Decimal("0.0812")])
    assert confere("A nota média foi 4.09.", [Decimal("4.0868")])
