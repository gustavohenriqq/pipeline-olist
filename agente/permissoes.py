"""Usuario somente leitura do agente: a defesa que nao depende do modelo obedecer.

Mesmo que a guarda de SQL falhe, o banco recusa escrita, consulta longa e
tabela fora da lista. As permissoes sao concedidas tabela por tabela, e precisam
ser reaplicadas depois de cada publicacao no Neon (DROP + CREATE apaga GRANT).
"""
from __future__ import annotations

from psycopg2 import sql

from agente.config import ROLE, SCHEMA, TABELAS_PERMITIDAS, TIMEOUT_MS


def papel_existe(cur) -> bool:
    cur.execute("select 1 from pg_roles where rolname = %s", (ROLE,))
    return cur.fetchone() is not None


def aplicar_permissoes(cur, senha: str | None = None) -> list[str]:
    """Cria (se preciso) e configura o papel do agente; devolve as tabelas concedidas."""
    papel = sql.Identifier(ROLE)
    schema = sql.Identifier(SCHEMA)
    if not papel_existe(cur):
        if not senha:
            raise ValueError("o papel do agente nao existe e nenhuma senha foi dada")
        cur.execute(sql.SQL("create role {} login password {}").format(papel, sql.Literal(senha)))
    elif senha:
        cur.execute(sql.SQL("alter role {} with login password {}").format(papel, sql.Literal(senha)))

    cur.execute(sql.SQL("alter role {} connection limit 3").format(papel))
    cur.execute(sql.SQL("alter role {} set default_transaction_read_only = on").format(papel))
    cur.execute(sql.SQL("alter role {} set statement_timeout = {}").format(
        papel, sql.Literal(f"{TIMEOUT_MS}ms")))

    # Comeca do zero no schema: nada concedido antes sobrevive por engano.
    cur.execute(sql.SQL("revoke all on all tables in schema {} from {}").format(schema, papel))
    cur.execute(sql.SQL("grant usage on schema {} to {}").format(schema, papel))

    cur.execute(
        "select table_name from information_schema.tables where table_schema = %s",
        (SCHEMA,),
    )
    existentes = {r[0] for r in cur.fetchall()}
    concedidas = [t for t in TABELAS_PERMITIDAS if t in existentes]
    for tabela in concedidas:
        cur.execute(sql.SQL("grant select on {}.{} to {}").format(
            schema, sql.Identifier(tabela), papel))
    return concedidas
