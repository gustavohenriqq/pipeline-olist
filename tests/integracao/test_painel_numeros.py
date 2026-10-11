"""Numeros do painel contra o banco (local ou CI) e contra o esperado do Power BI.

Os casos de dashboards/powerbi/conferencia/esperado.sql sao a mesma referencia que
confere o modelo do Power BI: se o painel web divergir, este teste acusa.
"""
from pathlib import Path

import psycopg2
import pytest

from agente.banco import executar
from ingestion.config import PG

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def conexao():
    try:
        conn = psycopg2.connect(**PG)
    except psycopg2.OperationalError:
        pytest.skip("Postgres indisponivel")
    yield conn
    conn.close()


def test_executar_com_parametro(conexao):
    assert executar(conexao, "select %s::int + 1 as n", (41,)) == (["n"], [(42,)])
