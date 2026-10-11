"""Consultas do painel sem banco: filtro sempre como parametro, nunca no texto do SQL."""
from datetime import date

import pytest

from painel import consultas
from painel.consultas import delta
from painel.filtros import Filtros


class _Cursor:
    def __init__(self, gravados):
        self.gravados = gravados
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, parametros=None):
        self.gravados.append((sql, parametros))


class _Conexao:
    closed = 0

    def __init__(self):
        self.gravados = []

    def cursor(self):
        return _Cursor(self.gravados)

    def rollback(self):
        pass


def _executa(funcao, f):
    conexao = _Conexao()
    funcao(conexao, f)
    return conexao.gravados[-1]


FILTRO = Filtros(date(2018, 1, 1), date(2018, 8, 31), "Nordeste")
EXECUTIVO = [consultas.cartoes_executivo, consultas.receita_mensal, consultas.placar_mensal]


@pytest.mark.parametrize("funcao", EXECUTIVO)
def test_filtro_vai_como_parametro_nunca_no_texto(funcao):
    sql, params = _executa(funcao, FILTRO)
    assert "Nordeste" not in sql and "2018-01-01" not in sql
    assert "Nordeste" in params.values() and date(2018, 1, 1) in params.values()


@pytest.mark.parametrize("funcao", EXECUTIVO)
def test_sem_linhas_devolve_tabela_vazia(funcao):
    assert funcao(_Conexao(), FILTRO).empty


def test_delta_de_valor_e_de_taxa():
    assert delta(110.0, 100.0, taxa=False) == pytest.approx(0.10)
    assert delta(0.95, 0.93, taxa=True) == pytest.approx(2.0)
    assert delta(10.0, None, taxa=False) is None
    assert delta(None, 10.0, taxa=True) is None
    assert delta(10.0, 0.0, taxa=False) is None
