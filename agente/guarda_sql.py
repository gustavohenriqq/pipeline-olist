"""Guarda de SQL: so leitura, so tabelas permitidas, sempre com LIMIT.

Segunda linha de defesa. A primeira e o usuario somente leitura do banco
(agente/permissoes.py): mesmo que algo passe por aqui, o banco recusa.
A analise e sintatica (sqlglot), nao por texto: comentario, caixa e espaco nao
enganam, e uma CTE que escreve (WITH x AS (DELETE ...)) aparece na arvore.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from agente.config import LIMITE_LINHAS, SCHEMA, TABELAS_PERMITIDAS

FUNCOES_NEGADAS = {
    "pg_sleep", "pg_sleep_for", "pg_sleep_until", "set_config", "dblink",
    "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "lo_import", "lo_export",
    "pg_terminate_backend", "pg_cancel_backend", "current_setting",
}

# Nos que escrevem, mudam estado ou travam linhas, em qualquer ponto da arvore.
NOS_NEGADOS = tuple(
    getattr(exp, nome) for nome in (
        "Insert", "Update", "Delete", "Drop", "Create", "Alter", "AlterTable",
        "Command", "Into", "Lock", "Merge", "TruncateTable", "Copy", "Set",
        "Transaction", "Commit", "Rollback", "Grant",
    ) if hasattr(exp, nome)
)


class SQLRecusado(Exception):
    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


def _nome_funcao(funcao: exp.Func) -> str:
    if isinstance(funcao, exp.Anonymous):
        return funcao.name.lower()
    return funcao.sql(dialect="postgres").split("(")[0].strip().lower()


def validar(sql: str) -> str:
    """Devolve o SQL pronto para executar, com LIMIT; levanta SQLRecusado se nao puder."""
    if not sql or not sql.strip():
        raise SQLRecusado("O modelo não gerou SQL.")
    try:
        comandos = [c for c in sqlglot.parse(sql, read="postgres") if c is not None]
    except ParseError:
        raise SQLRecusado("Não consegui ler o SQL gerado.") from None
    if len(comandos) != 1:
        raise SQLRecusado("Só é permitido um comando por consulta.")
    raiz = comandos[0]

    if not isinstance(raiz, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise SQLRecusado("Só consultas de leitura (SELECT) são permitidas.")
    for no in raiz.walk():
        if isinstance(no, NOS_NEGADOS):
            raise SQLRecusado("A consulta tenta escrever ou travar dados.")

    ctes = {cte.alias_or_name for cte in raiz.find_all(exp.CTE)}
    for tabela in raiz.find_all(exp.Table):
        nome, schema = tabela.name, tabela.db
        if not nome:
            raise SQLRecusado("Fonte de dados não permitida.")
        if not schema and nome in ctes:
            continue
        if (schema and schema != SCHEMA) or nome not in TABELAS_PERMITIDAS:
            raise SQLRecusado(f"A tabela {tabela.sql(dialect='postgres')} não está liberada para o agente.")

    for funcao in raiz.find_all(exp.Func):
        if _nome_funcao(funcao) in FUNCOES_NEGADAS:
            raise SQLRecusado(f"A função {_nome_funcao(funcao)} não é permitida.")

    limite = raiz.args.get("limit")
    atual = None
    if limite is not None:
        valor = limite.args.get("expression")
        if isinstance(valor, exp.Literal) and valor.is_int:
            atual = int(valor.name)
    if atual is None or atual > LIMITE_LINHAS:
        raiz.set("limit", exp.Limit(expression=exp.Literal.number(LIMITE_LINHAS)))
    return raiz.sql(dialect="postgres")
