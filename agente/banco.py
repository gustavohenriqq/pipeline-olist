"""Execucao do SQL do agente no usuario somente leitura."""
from __future__ import annotations

import psycopg2

from agente.config import TIMEOUT_MS, env


class ErroBanco(Exception):
    """Erro do banco ao executar o SQL; a mensagem volta para o modelo corrigir."""


class BancoIndisponivel(Exception):
    """A conexao caiu ou nao abriu (Neon dormindo, rede): nao adianta o modelo tentar de novo."""


def _desfazer(conexao) -> None:
    # Com a conexao derrubada, o proprio rollback levanta InterfaceError.
    if not conexao.closed:
        try:
            conexao.rollback()
        except psycopg2.Error:
            pass


def abrir_conexao():
    host = env("AGENTE_DB_HOST", "localhost")
    parametros = {
        "host": host,
        "port": env("AGENTE_DB_PORT", "5432"),
        "dbname": env("AGENTE_DB_NAME", "olist"),
        "user": env("AGENTE_DB_USER", "agente_leitura"),
        "password": env("AGENTE_DB_PASSWORD"),
        "connect_timeout": 15,
        "application_name": "agente-olist",
    }
    if host not in ("localhost", "127.0.0.1"):
        parametros["sslmode"] = "require"
    return psycopg2.connect(**parametros)


def ler_atualizacao(conexao) -> str | None:
    """Resumo da ultima atualizacao dos dados (rodape do app); None se nao houver."""
    try:
        with conexao.cursor() as cur:
            cur.execute("SELECT resumo FROM marts.atualizacao_dados LIMIT 1")
            linha = cur.fetchone()
        conexao.rollback()
        return linha[0] if linha else None
    except psycopg2.Error:
        _desfazer(conexao)
        return None


def executar(conexao, sql: str, parametros: tuple | None = None) -> tuple[list[str], list[tuple]]:
    """Roda em transacao somente leitura com tempo maximo; devolve colunas e linhas.

    `parametros` vai separado do texto (psycopg2 faz o escape): o painel nunca
    concatena filtro em SQL.
    """
    try:
        with conexao.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(f"SET LOCAL statement_timeout = {int(TIMEOUT_MS)}")
            cur.execute(sql, parametros)
            colunas = [d[0] for d in cur.description or []]
            linhas = cur.fetchall() if cur.description else []
        conexao.rollback()
        return colunas, linhas
    except psycopg2.Error as erro:
        _desfazer(conexao)
        if conexao.closed or isinstance(erro, psycopg2.InterfaceError):
            raise BancoIndisponivel(str(erro).strip()) from None
        mensagem = (getattr(erro, "pgerror", None) or str(erro)).strip().splitlines()
        raise ErroBanco(mensagem[0] if mensagem else "erro no banco") from None
