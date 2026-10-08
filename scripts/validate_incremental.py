"""Regressao incremental na amostra, em um banco descartavel (nunca no alvo).

Usa o mesmo Postgres/perfil do CI; o usuario precisa de CREATEDB.
Executar: python scripts/validate_incremental.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from contextlib import closing
from pathlib import Path

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ingestion"))
from config import PG  # noqa: E402

FACTS = {"fato_pedidos": "pedido_sk", "fato_itens_pedido": "item_sk"}


def connect(database):
    return psycopg2.connect(
        host=PG["host"], port=PG["port"], user=PG["user"],
        password=PG["password"], dbname=database,
    )


def snapshot(database, *, physical=False):
    """Conteudo completo; opcionalmente inclui tupla/versao para detectar escritas."""
    result = {}
    with closing(connect(database)) as conn, conn.cursor() as cur:
        for table, key in FACTS.items():
            extra = ", ctid::text, xmin::text" if physical else ""
            cur.execute(sql.SQL("select *{} from marts.{} order by {}").format(
                sql.SQL(extra), sql.Identifier(table), sql.Identifier(key),
            ))
            rows = cur.fetchall()
            assert len(rows) == len({row[0] for row in rows}), f"Chave duplicada: {table}"
            result[table] = rows
    return result


def clone_order_rows(cur, table, old_order, new_order):
    """Copia um pedido e seus filhos, conservando as chaves de item/pagamento."""
    cur.execute(sql.SQL("select * from raw.{} limit 0").format(sql.Identifier(table)))
    columns = [column.name for column in cur.description]
    expressions = [sql.Placeholder() if column == "order_id" else sql.Identifier(column)
                   for column in columns]
    cur.execute(sql.SQL(
        "insert into raw.{} ({}) select {} from raw.{} where order_id = %s"
    ).format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(expressions), sql.Identifier(table),
    ), (new_order, old_order))
    return cur.rowcount


def change_sample(database):
    """Novos registros antigos + correcoes em status, NULL, itens, pagamento e nota."""
    new_order = uuid.uuid4().hex
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("""
            select o.order_id, o.order_purchase_timestamp
            from raw.orders o
            where exists (select 1 from raw.order_items i where i.order_id = o.order_id)
              and exists (select 1 from raw.order_payments p where p.order_id = o.order_id)
              and exists (select 1 from raw.order_reviews r where r.order_id = o.order_id)
              and nullif(o.order_delivered_customer_date, '') is not null
            order by o.order_purchase_timestamp, o.order_id limit 1
        """)
        old_order, purchased_at = cur.fetchone()
        cur.execute("select max(order_purchase_timestamp) from raw.orders")
        assert purchased_at < cur.fetchone()[0], "A fixture precisa de um pedido antigo"

        clone_order_rows(cur, "orders", old_order, new_order)
        cloned_items = clone_order_rows(cur, "order_items", old_order, new_order)
        clone_order_rows(cur, "order_payments", old_order, new_order)
        clone_order_rows(cur, "order_reviews", old_order, new_order)

        cur.execute("""
            update raw.orders set order_status = 'shipped', order_delivered_customer_date = ''
            where order_id = %s
        """, (old_order,))
        cur.execute("""
            update raw.order_items set price = (price::numeric + 13)::text
            where order_id = %s
        """, (old_order,))
        cur.execute("""
            update raw.order_payments set payment_value = (payment_value::numeric + 17)::text
            where order_id = %s
        """, (old_order,))
        cur.execute("""
            update raw.order_reviews set review_score = (case when review_score = '1'
                then 5 else 1 end)::text where order_id = %s
        """, (old_order,))
        # Um item que chegou depois, ainda ligado ao pedido antigo.
        cur.execute("""
            insert into raw.order_items
            select order_id,
                (select (max(order_item_id::integer) + 1)::text from raw.order_items
                    where order_id = %s),
                product_id, seller_id, shipping_limit_date, '23', '7'
            from raw.order_items where order_id = %s order by order_item_id limit 1
        """, (old_order, old_order))
        conn.commit()
    return old_order, new_order, cloned_items


def assert_updated(database, old_order):
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("""
            select order_status, delivered_customer_at, valor_itens, valor_pago, nota_avaliacao
            from marts.fato_pedidos where order_id = %s
        """, (old_order,))
        status, delivered, items, paid, score = cur.fetchone()
        assert status == 'shipped' and delivered is None, "Correcao antiga/NULL nao aplicada"
        cur.execute("select sum(price::numeric) from raw.order_items where order_id = %s", (old_order,))
        assert items == cur.fetchone()[0], "Item antigo/novo nao atualizado no agregado"
        cur.execute("select sum(payment_value::numeric) from raw.order_payments where order_id = %s", (old_order,))
        assert paid == cur.fetchone()[0], "Pagamento antigo nao atualizado"
        cur.execute("select distinct review_score::integer from raw.order_reviews where order_id = %s", (old_order,))
        assert score in {row[0] for row in cur.fetchall()}, "Avaliacao antiga nao atualizada"


def dbt(env, *args, check=True):
    """Roda um comando dbt no banco descartavel e devolve o processo (saida capturada)."""
    proc = subprocess.run([sys.executable, "-m", "dbt.cli.main", *args, "--profiles-dir", "."],
                          cwd=ROOT / "dbt", env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        print(proc.stdout[-3000:], proc.stderr[-3000:])
        raise AssertionError(f"dbt {' '.join(args)} falhou")
    return proc


def check_freshness(database, env):
    """A carga recem-feita passa; com 2 dias avisa; com 8 dias da erro."""
    def idade(intervalo):
        with closing(connect(database)) as conn, conn.cursor() as cur:
            cur.execute(f"update raw.orders set _carregado_em = now() - interval '{intervalo}'")
            conn.commit()

    proc = dbt(env, "source", "freshness", check=False)
    assert proc.returncode == 0, "Freshness falhou logo depois da carga:\n" + proc.stdout[-2000:]
    idade("2 days")
    proc = dbt(env, "source", "freshness", check=False)
    assert proc.returncode == 0 and "WARN" in proc.stdout, "Carga de 2 dias deveria avisar"
    idade("8 days")
    proc = dbt(env, "source", "freshness", check=False)
    assert proc.returncode != 0 and "ERROR" in proc.stdout, "Carga de 8 dias deveria dar erro"
    idade("0 days")
    print("OK: freshness passa na carga nova, avisa com 2 dias e falha com 8", flush=True)


def execucoes(database):
    """Quantas invocacoes do dbt ja foram registradas (0 antes da primeira)."""
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("select to_regclass('meta.execucoes_dbt') is not null")
        if not cur.fetchone()[0]:
            return 0
        cur.execute("select count(*) from meta.execucoes_dbt")
        return cur.fetchone()[0]


def check_metadados(database, antes, comando="build"):
    """Uma linha nova por invocacao, com contagens coerentes com os resultados por no."""
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("select count(*) from meta.execucoes_dbt")
        assert cur.fetchone()[0] == antes + 1, "Execucao do dbt nao registrada (ou registrada em dobro)"
        cur.execute("""
            select invocation_id, comando, nos, sucesso + aviso + erro + pulados
            from meta.execucoes_dbt order by terminado_em desc limit 1
        """)
        invocacao, cmd, nos, soma = cur.fetchone()
        assert cmd == comando, f"Comando registrado {cmd!r}, esperado {comando!r}"
        assert nos == soma, "Contagens por status nao somam o total de nos"
        cur.execute("select count(*) from meta.resultados_dbt where invocation_id = %s", (invocacao,))
        assert cur.fetchone()[0] == nos, "resultados_dbt nao tem uma linha por no"
        cur.execute("select count(*), min(resumo) from marts.atualizacao_dados")
        linhas, resumo = cur.fetchone()
        assert linhas == 1 and resumo.startswith("Dados processados em"), "atualizacao_dados invalida"


def check_metadados_extras(database, env):
    """dbt test sozinho nao mexe no rodape; texto com aspas e escapado."""
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("select processado_em from marts.atualizacao_dados")
        processado = cur.fetchone()[0]
    antes = execucoes(database)
    dbt(env, "test")
    check_metadados(database, antes, comando="test")
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("select processado_em from marts.atualizacao_dados")
        assert cur.fetchone()[0] == processado, "dbt test alterou atualizacao_dados"
    dbt(env, "run-operation", "testa_texto_sql")
    print("OK: metadados por invocacao; dbt test nao altera o rodape; aspas escapadas", flush=True)


JANELA = "{janela_inicio: '2018-03-01', janela_fim: '2018-04-01'}"


def linhas_da_janela(database):
    """Conteudo dos dois fatos para compras de marco/2018, por chave."""
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("""select * from marts.fato_pedidos
            where purchased_at >= '2018-03-01' and purchased_at < '2018-04-01' order by pedido_sk""")
        pedidos = {row[0]: row for row in cur.fetchall()}
        cur.execute("""select * from marts.fato_itens_pedido
            where tempo_sk_compra >= 20180301 and tempo_sk_compra < 20180401 order by item_sk""")
        itens = {row[0]: row for row in cur.fetchall()}
    return pedidos, itens


def check_janela(database, env, build):
    """Reprocessar marco/2018 remove o pedido apagado ali e ignora mudanca fora dela."""
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("""
            select o.order_id from raw.orders o
            where o.order_purchase_timestamp >= '2018-03-01' and o.order_purchase_timestamp < '2018-04-01'
              and exists (select 1 from raw.order_items i where i.order_id = o.order_id)
            order by o.order_id limit 1""")
        alvo = cur.fetchone()[0]
        cur.execute("""
            select order_id, order_status from raw.orders
            where order_purchase_timestamp < '2018-01-01' and order_status = 'delivered'
            order by order_id limit 1""")
        fora, status_fora = cur.fetchone()
        pedidos_antes, itens_antes = linhas_da_janela(database)
        for tabela in ("order_items", "order_payments", "order_reviews", "orders"):
            cur.execute(sql.SQL("delete from raw.{} where order_id = %s").format(sql.Identifier(tabela)), (alvo,))
        cur.execute("update raw.orders set order_status = 'shipped' where order_id = %s", (fora,))
        conn.commit()

    build("--select", "fato_pedidos", "fato_itens_pedido", "--vars", JANELA)
    pedidos, itens = linhas_da_janela(database)
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("select count(*) from marts.fato_pedidos where order_id = %s", (alvo,))
        assert cur.fetchone()[0] == 0, "Pedido apagado na origem continua no fato_pedidos"
        cur.execute("select count(*) from marts.fato_itens_pedido where order_id = %s", (alvo,))
        assert cur.fetchone()[0] == 0, "Itens do pedido apagado continuam no fato_itens_pedido"
        cur.execute("select order_status from marts.fato_pedidos where order_id = %s", (fora,))
        assert cur.fetchone()[0] == status_fora, "Mudanca fora da janela foi aplicada"
    assert {k: v for k, v in pedidos_antes.items() if v[1] != alvo} == pedidos, \
        "Outras linhas de marco mudaram em fato_pedidos"
    assert {k: v for k, v in itens_antes.items() if v[1] != alvo} == itens, \
        "Outras linhas de marco mudaram em fato_itens_pedido"

    build()
    with closing(connect(database)) as conn, conn.cursor() as cur:
        cur.execute("select order_status from marts.fato_pedidos where order_id = %s", (fora,))
        assert cur.fetchone()[0] == "shipped", "Build normal nao aplicou a mudanca fora da janela"
    incremental = snapshot(database)
    build("--full-refresh")
    assert snapshot(database) == incremental, "Depois da janela, incremental difere do full-refresh"

    proc = dbt(env, "compile", "--select", "fato_pedidos", "--vars", "{janela_inicio: '2018-03-01'}", check=False)
    assert proc.returncode != 0 and "janela_fim" in proc.stdout, "Janela so com inicio deveria falhar"
    proc = dbt(env, "compile", "--select", "fato_pedidos", "--vars",
               "{janela_inicio: '2018-04-01', janela_fim: '2018-03-01'}", check=False)
    assert proc.returncode != 0, "Janela com inicio depois do fim deveria falhar"
    print("OK: janela remove o apagado, ignora o de fora, iguala o full-refresh e rejeita vars invalidas",
          flush=True)


def main():
    database = "olist_incremental_check_" + uuid.uuid4().hex
    env = dict(os.environ, POSTGRES_DB=database, OLIST_DATA_DIR=str(ROOT / "data/sample"))
    # A config Python ja resolveu o .env; dbt recebe os mesmos valores explicitamente.
    env.update(POSTGRES_HOST=PG["host"], POSTGRES_PORT=PG["port"],
               POSTGRES_USER=PG["user"], POSTGRES_PASSWORD=PG["password"])

    def build(*args):
        antes = execucoes(database)
        subprocess.run([sys.executable, "-m", "dbt.cli.main", "build", "--profiles-dir", ".", *args],
                       cwd=ROOT / "dbt", env=env, check=True)
        check_metadados(database, antes)

    with closing(connect(PG["dbname"])) as admin:
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(sql.SQL("create database {}").format(sql.Identifier(database)))
        try:
            subprocess.run([sys.executable, str(ROOT / "ingestion/ingest.py")],
                           cwd=ROOT, env=env, check=True)
            check_freshness(database, env)
            # Parse completo num build: os hooks sao renderizados sem o grafo
            # carregado, e uma macro que use graph/results sem "execute" quebra aqui.
            build("--no-partial-parse")
            baseline = snapshot(database, physical=True)
            build()
            assert snapshot(database, physical=True) == baseline, "Reexecucao reescreveu/duplicou fatos"
            print("OK: build repetido conserva linhas e versoes fisicas", flush=True)
            check_metadados_extras(database, env)

            old_order, new_order, cloned_items = change_sample(database)
            build()
            assert_updated(database, old_order)
            changed = snapshot(database, physical=True)
            assert len(changed['fato_pedidos']) == len(baseline['fato_pedidos']) + 1
            assert len(changed['fato_itens_pedido']) == len(baseline['fato_itens_pedido']) + cloned_items + 1
            for table in FACTS:
                untouched = {row[0]: row for row in baseline[table]
                             if row[1] not in (old_order, new_order)}
                assert all(untouched[row[0]] == row for row in changed[table] if row[0] in untouched), \
                    f"Registro sem alteracao foi reescrito: {table}"
            print("OK: novos registros antigos e correcoes aplicados; demais linhas preservadas", flush=True)

            build()
            assert snapshot(database, physical=True) == changed, "Reexecucao apos delta nao e idempotente"
            incremental = snapshot(database)
            build("--full-refresh")
            assert snapshot(database) == incremental, "Resultado incremental difere do full-refresh"
            print("OK: delta idempotente e identico ao full-refresh em todas as colunas dos fatos", flush=True)
            check_janela(database, env, build)
        finally:
            with admin.cursor() as cur:
                cur.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(database)))


if __name__ == "__main__":
    main()
