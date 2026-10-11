"""Conexao perdida (Neon dormiu, rede caiu): vira BancoIndisponivel, nunca InterfaceError."""
import psycopg2
import pytest

from agente.banco import BancoIndisponivel, executar, ler_atualizacao


class _Cursor:
    def __init__(self, conexao):
        self.conexao = conexao

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, *a, **k):
        self.conexao.closed = 2
        raise psycopg2.OperationalError("server closed the connection unexpectedly")


class _ConexaoMorta:
    """Como o psycopg2 se comporta quando o servidor derruba a conexao."""

    closed = 0

    def cursor(self):
        return _Cursor(self)

    def rollback(self):
        if self.closed:
            raise psycopg2.InterfaceError("connection already closed")


def test_conexao_derrubada_vira_banco_indisponivel():
    with pytest.raises(BancoIndisponivel):
        executar(_ConexaoMorta(), "SELECT 1")


def test_rodape_com_conexao_derrubada_devolve_none():
    assert ler_atualizacao(_ConexaoMorta()) is None
