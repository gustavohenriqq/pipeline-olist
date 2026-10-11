"""Permissoes reais do usuario do agente, contra o Postgres do .env (local ou CI).

Roda depois do dbt build no CI. Se alguma tabela das marts nao existir (PR que
nao construiu models), cria uma versao minima, so para o teste de permissao.
"""
import os

import psycopg2
import pytest
from psycopg2 import errors, sql

from agente.config import ROLE, SCHEMA, TABELAS_DO_APP, TABELAS_PERMITIDAS
from agente.permissoes import aplicar_permissoes
from ingestion.config import PG

SENHA = os.getenv("AGENTE_DB_PASSWORD") or "agente_teste_local_123"
TABELAS_PROIBIDAS = ("obt_pedidos", "seguranca_bi")


@pytest.fixture(scope="module")
def admin():
    try:
        conn = psycopg2.connect(**PG)
    except psycopg2.OperationalError:
        pytest.skip("Postgres indisponivel")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("create schema if not exists marts")
        cur.execute("create schema if not exists raw")
        for tabela in TABELAS_PERMITIDAS + TABELAS_DO_APP + TABELAS_PROIBIDAS:
            cur.execute(sql.SQL("create table if not exists {}.{} (id int)").format(
                sql.Identifier(SCHEMA), sql.Identifier(tabela)))
        cur.execute("create table if not exists raw.orders (id int)")
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def concedidas(admin):
    with admin.cursor() as cur:
        return aplicar_permissoes(cur, SENHA)


@pytest.fixture()
def agente(concedidas):
    conn = psycopg2.connect(host=PG["host"], port=PG["port"], dbname=PG["dbname"],
                            user=ROLE, password=SENHA)
    yield conn
    conn.close()


def _executar(conn, comando):
    with conn.cursor() as cur:
        cur.execute(comando)
        return cur.fetchall() if cur.description else None


def test_le_tabela_permitida(agente):
    assert _executar(agente, "select count(*) from marts.fato_pedidos")[0][0] >= 0


@pytest.mark.parametrize("tabela", TABELAS_PROIBIDAS)
def test_nao_le_obt_nem_seguranca(agente, tabela):
    with pytest.raises(errors.InsufficientPrivilege):
        _executar(agente, f"select * from marts.{tabela}")


def test_nao_le_raw(agente):
    with pytest.raises(errors.InsufficientPrivilege):
        _executar(agente, "select * from raw.orders")


@pytest.mark.parametrize("comando", [
    "create table marts.x (a int)",
    "delete from marts.dim_tempo",
])
def test_nao_escreve(agente, comando):
    with pytest.raises((errors.ReadOnlySqlTransaction, errors.InsufficientPrivilege)):
        _executar(agente, comando)


def test_timeout(agente):
    with pytest.raises(errors.QueryCanceled):
        _executar(agente, "select pg_sleep(6)")


def test_reaplicar_e_idempotente(admin, concedidas):
    with admin.cursor() as cur:
        assert aplicar_permissoes(cur) == concedidas
    assert set(concedidas) == set(TABELAS_PERMITIDAS + TABELAS_DO_APP)


def test_executar_devolve_colunas_e_linhas(agente):
    from agente.banco import executar
    colunas, linhas = executar(agente, "select count(*) as n, 1.5::numeric as v from marts.dim_tempo")
    assert colunas == ["n", "v"]
    assert len(linhas) == 1


def test_executar_converte_erro_e_segue_usavel(agente):
    from agente.banco import ErroBanco, executar
    with pytest.raises(ErroBanco) as erro:
        executar(agente, "select coluna_que_nao_existe from marts.dim_tempo")
    assert "coluna_que_nao_existe" in str(erro.value)
    assert executar(agente, "select 1 as um") == (["um"], [(1,)])


def test_executar_respeita_tempo_maximo(agente):
    from agente.banco import ErroBanco, executar
    with pytest.raises(ErroBanco):
        executar(agente, "select pg_sleep(6)")


def test_le_atualizacao_dados_para_o_rodape(agente):
    from agente.banco import ler_atualizacao
    assert ler_atualizacao(agente) is None or isinstance(ler_atualizacao(agente), str)


def test_conexao_derrubada_vira_banco_indisponivel(admin, concedidas):
    """Como quando o Neon dorme: o servidor encerra a sessao no meio do caminho."""
    from agente.banco import BancoIndisponivel, executar
    conn = psycopg2.connect(**{**PG, "user": ROLE, "password": SENHA})
    with conn.cursor() as cur:
        cur.execute("select pg_backend_pid()")
        pid = cur.fetchone()[0]
    conn.rollback()
    with admin.cursor() as cur:
        cur.execute("select pg_terminate_backend(%s)", (pid,))
    for _ in range(2):
        with pytest.raises(BancoIndisponivel):
            executar(conn, "select 1")
    conn.close()
