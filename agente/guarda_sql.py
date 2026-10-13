"""Guarda de SQL: so leitura, so tabelas permitidas, sempre com LIMIT.

Segunda linha de defesa. A primeira e o usuario somente leitura do banco
(agente/permissoes.py): mesmo que algo passe por aqui, o banco recusa.
A analise e sintatica (sqlglot), nao por texto: comentario, caixa e espaco nao
enganam, e uma CTE que escreve (WITH x AS (DELETE ...)) aparece na arvore.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from agente.config import LIMITE_LINHAS, SCHEMA, TABELAS_PERMITIDAS

FUNCOES_NEGADAS = {
    "set_config", "current_setting", "version", "inet_server_addr", "inet_server_port",
    "inet_client_addr", "inet_client_port", "txid_current",
}
# Familias inteiras: funcoes do servidor (pg_*), objetos grandes (lo_*), conexao a
# outros bancos (dblink*) e as que executam SQL em texto (query_to_xml, *_to_xml).
PREFIXOS_NEGADOS = ("pg_", "lo_", "dblink", "query_to_", "cursor_to_")
SUFIXOS_NEGADOS = ("_to_xml", "_to_xmlschema", "_to_xml_and_xmlschema")


def _funcao_negada(nome: str) -> bool:
    return (nome in FUNCOES_NEGADAS or nome.startswith(PREFIXOS_NEGADOS)
            or nome.endswith(SUFIXOS_NEGADOS))


def _nome(identificador) -> str:
    """Nome como o Postgres enxerga: sem aspas e dobrado para minusculas; com aspas, como escrito.

    MARTS.FATO_PEDIDOS e marts.fato_pedidos sao a mesma tabela; marts."FATO_PEDIDOS" e outra.
    """
    if not isinstance(identificador, exp.Identifier):
        return ""
    return identificador.name if identificador.quoted else identificador.name.lower()


def _ctes_visiveis(tabela: exp.Table) -> set[str]:
    """CTEs que alcancam esta tabela: as do WITH da propria consulta e das que a envolvem.

    Uma CTE definida dentro de uma subconsulta nao vale fora dela; sem isso,
    "(WITH pg_roles AS (...) ...) CROSS JOIN pg_roles" liberaria o catalogo.
    """
    nomes, no = set(), tabela.parent
    while no is not None:
        # "with_" nas versoes novas do sqlglot, "with" nas antigas
        com = (no.args.get("with_") or no.args.get("with")) if isinstance(no, exp.Expression) else None
        if com is not None:
            nomes |= {_nome(cte.args["alias"].this) if cte.args.get("alias") else cte.alias_or_name
                      for cte in com.expressions}
        no = no.parent
    return nomes


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
    except (SqlglotError, RecursionError):
        raise SQLRecusado("Não consegui ler o SQL gerado.") from None
    if len(comandos) != 1:
        raise SQLRecusado("Só é permitido um comando por consulta.")
    raiz = comandos[0]

    if not isinstance(raiz, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise SQLRecusado("Só consultas de leitura (SELECT) são permitidas.")
    for no in raiz.walk():
        if isinstance(no, NOS_NEGADOS):
            raise SQLRecusado("A consulta tenta escrever ou travar dados.")

    for tabela in raiz.find_all(exp.Table):
        nome, schema = _nome(tabela.this), _nome(tabela.args.get("db"))
        if not nome:
            raise SQLRecusado("Fonte de dados não permitida.")
        if not schema and nome in _ctes_visiveis(tabela):
            continue
        if (schema and schema != SCHEMA) or nome not in TABELAS_PERMITIDAS:
            raise SQLRecusado(f"A tabela {tabela.sql(dialect='postgres')} não está liberada para o agente.")

    for funcao in raiz.find_all(exp.Func):
        if _funcao_negada(_nome_funcao(funcao)):
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
