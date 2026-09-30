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


def main():
    database = "olist_incremental_check_" + uuid.uuid4().hex
    env = dict(os.environ, POSTGRES_DB=database, OLIST_DATA_DIR=str(ROOT / "data/sample"))
    # A config Python ja resolveu o .env; dbt recebe os mesmos valores explicitamente.
    env.update(POSTGRES_HOST=PG["host"], POSTGRES_PORT=PG["port"],
               POSTGRES_USER=PG["user"], POSTGRES_PASSWORD=PG["password"])

    def build(*args):
        subprocess.run([sys.executable, "-m", "dbt.cli.main", "build", "--profiles-dir", ".", *args],
                       cwd=ROOT / "dbt", env=env, check=True)

    with closing(connect(PG["dbname"])) as admin:
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(sql.SQL("create database {}").format(sql.Identifier(database)))
        try:
            subprocess.run([sys.executable, str(ROOT / "ingestion/ingest.py")],
                           cwd=ROOT, env=env, check=True)
            build()
            baseline = snapshot(database, physical=True)
            build()
            assert snapshot(database, physical=True) == baseline, "Reexecucao reescreveu/duplicou fatos"
            print("OK: build repetido conserva linhas e versoes fisicas", flush=True)

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
        finally:
            with admin.cursor() as cur:
                cur.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(database)))


if __name__ == "__main__":
    main()
