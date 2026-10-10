"""Guarda de SQL: so SELECT sobre as tabelas permitidas, com LIMIT."""
import re

import pytest

from agente.guarda_sql import SQLRecusado, validar


def _limite(sql: str) -> int | None:
    achado = re.search(r"\bLIMIT\s+(\d+)\s*$", sql, re.IGNORECASE)
    return int(achado.group(1)) if achado else None


@pytest.mark.parametrize("sql", [
    "SELECT count(*) FROM fato_pedidos",
    "select uf, count(*) from dim_clientes group by uf",
    "SELECT * FROM marts.dim_tempo",
    "WITH m AS (SELECT tempo_sk_compra, valor_total FROM fato_pedidos) "
    "SELECT t.ano, sum(m.valor_total) FROM m JOIN dim_tempo t ON t.tempo_sk = m.tempo_sk_compra GROUP BY t.ano",
    "WITH qualquer_nome AS (SELECT 1 AS x) SELECT x FROM qualquer_nome",
    "SELECT uf FROM dim_clientes UNION SELECT uf FROM dim_vendedores",
])
def test_aceita_select_permitido_com_limite(sql):
    assert _limite(validar(sql)) == 1000


def test_mantem_limite_menor():
    assert _limite(validar("SELECT * FROM dim_tempo LIMIT 10")) == 10


def test_reduz_limite_maior():
    assert _limite(validar("SELECT * FROM dim_tempo LIMIT 5000")) == 1000


@pytest.mark.parametrize("sql", [
    "SELECT 1; DROP TABLE marts.fato_pedidos",
    "DELETE FROM fato_pedidos",
    "UPDATE fato_pedidos SET valor_total = 0",
    "INSERT INTO dim_tempo (tempo_sk) VALUES (1)",
    "DROP TABLE fato_pedidos",
    "CREATE TABLE x AS SELECT * FROM fato_pedidos",
    "WITH x AS (DELETE FROM fato_pedidos RETURNING *) SELECT * FROM x",
    "SELECT * INTO marts.copia FROM fato_pedidos",
    "SELECT * FROM fato_pedidos FOR UPDATE",
    "SELECT * FROM obt_pedidos",
    "SELECT * FROM seguranca_bi",
    "SELECT * FROM marts.seguranca_bi",
    "SELECT * FROM raw.orders",
    "SELECT * FROM meta.execucoes_dbt",
    "SELECT * FROM pg_catalog.pg_user",
    "SELECT * FROM information_schema.tables",
    "SELECT pg_sleep(10)",
    "SELECT set_config('statement_timeout', '0', false)",
    "SELECT * FROM dblink('x', 'y') AS t(a int)",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT current_setting('data_directory')",
    "",
    "   ",
    "isso nao e sql",
])
def test_recusa(sql):
    with pytest.raises(SQLRecusado) as erro:
        validar(sql)
    assert erro.value.motivo


def test_comando_escondido_em_comentario_nao_passa():
    with pytest.raises(SQLRecusado):
        validar("SELECT 1 /* inocente */; DELETE FROM fato_pedidos -- fim")
