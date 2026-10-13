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


def test_literal_sem_fechar_e_recusado_sem_excecao_crua():
    for sql in ("SELECT 'abc FROM marts.fato_pedidos",
                "SELECT * FROM marts.dim_clientes WHERE cidade = 'santa barbara d'oeste'"):
        with pytest.raises(SQLRecusado):
            validar(sql)


def test_aninhamento_profundo_e_recusado():
    with pytest.raises(SQLRecusado):
        validar("SELECT " + "(" * 3000 + "1" + ")" * 3000)


def test_cte_de_subconsulta_nao_libera_nome_de_fora():
    with pytest.raises(SQLRecusado):
        validar("SELECT r.rolname FROM (WITH pg_roles AS (SELECT 1) SELECT 1) a CROSS JOIN pg_roles r")


def test_tabela_do_catalogo_sem_schema_e_recusada():
    with pytest.raises(SQLRecusado):
        validar("SELECT rolname FROM pg_roles")


def test_cte_continua_valendo_no_proprio_escopo_e_em_subconsulta():
    validar("WITH t AS (SELECT 1 AS x FROM marts.fato_pedidos) SELECT x FROM t")
    validar("WITH t AS (SELECT 1 AS x FROM marts.fato_pedidos) SELECT (SELECT max(x) FROM t)")


def test_funcoes_que_executam_sql_ou_leem_o_servidor_sao_recusadas():
    for chamada in ("query_to_xml('select 1', true, true, '')", "table_to_xml('marts.fato_pedidos', true, true, '')",
                    "version()", "inet_server_addr()", "lo_get(1)", "pg_stat_file('x')",
                    "pg_advisory_lock(1)", "dblink_exec('x')"):
        with pytest.raises(SQLRecusado):
            validar(f"SELECT {chamada} FROM marts.fato_pedidos")


@pytest.mark.parametrize("sql", [
    "SELECT count(*) FROM MARTS.FATO_PEDIDOS",
    "select * from Marts.Dim_Tempo",
    "SELECT count(*) FROM FATO_PEDIDOS",
    'SELECT count(*) FROM "marts"."fato_pedidos"',
    "WITH M AS (SELECT 1 AS x FROM marts.fato_pedidos) SELECT x FROM m",
])
def test_identificador_sem_aspas_nao_diferencia_maiusculas(sql):
    # no Postgres, nome sem aspas e dobrado para minusculas: MARTS.FATO_PEDIDOS e marts.fato_pedidos
    assert _limite(validar(sql)) == 1000


@pytest.mark.parametrize("sql", [
    'SELECT * FROM marts."FATO_PEDIDOS"',
    'SELECT * FROM "MARTS".fato_pedidos',
    'SELECT * FROM "Fato_Pedidos"',
    "SELECT * FROM PG_CATALOG.PG_USER",
    "SELECT * FROM MARTS.SEGURANCA_BI",
    'WITH "Pg_roles" AS (SELECT 1) SELECT * FROM pg_roles',
])
def test_nome_entre_aspas_continua_diferenciando_maiusculas(sql):
    # entre aspas o Postgres respeita a caixa: "FATO_PEDIDOS" e outra tabela
    with pytest.raises(SQLRecusado):
        validar(sql)
