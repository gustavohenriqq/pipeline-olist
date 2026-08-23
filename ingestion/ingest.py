"""Ingestao dos CSVs do Olist para o schema raw do Postgres.

Padrao adotado (camada "bronze"/raw):
  - A camada raw guarda o dado quase como veio: todas as colunas como TEXT.
  - Nenhum casting de tipo aqui. Isso fica no staging do dbt, que e versionado
    e testavel. Assim, se o casting mudar, e uma alteracao rastreavel no Git,
    e o dado bruto continua intacto para reprocessar.

Por que COPY e nao df.to_sql linha a linha?
  - to_sql faz INSERT em lote, mas ainda e ordens de grandeza mais lento.
  - A geolocation tem ~1 milhao de linhas. COPY carrega tudo em segundos.
  - COPY e a ferramenta nativa do Postgres para carga em massa.

Uso:
    python ingestion/ingest.py
"""
from __future__ import annotations

import io
import sys
import time

import pandas as pd
import psycopg2

from config import CSV_TO_TABLE, PG, RAW_DIR, RAW_SCHEMA


def connect():
    return psycopg2.connect(
        host=PG["host"],
        port=PG["port"],
        dbname=PG["dbname"],
        user=PG["user"],
        password=PG["password"],
    )


def read_csv_as_text(path) -> pd.DataFrame:
    """Le o CSV preservando tudo como texto.

    - encoding utf-8-sig remove o BOM do arquivo de traducao de categorias.
    - dtype=str evita que o pandas "adivinhe" tipos (ex: zip virar float).
    - keep_default_na=False mantem strings vazias como '' (o staging troca por NULL).
    - O pandas resolve virgulas e quebras de linha dentro de campos com aspas
      (importante nas mensagens de avaliacao).
    """
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )


def create_schema(cur) -> None:
    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{RAW_SCHEMA}";')


def load_table(cur, table: str, df: pd.DataFrame) -> None:
    cols = list(df.columns)
    cols_ddl = ", ".join(f'"{c}" TEXT' for c in cols)

    # CASCADE porque as views de staging do dbt dependem das tabelas raw.
    # Ao reingerir, derrubamos as views junto; o proximo "dbt run" as recria.
    # (A ordem correta do fluxo e sempre: ingest -> dbt run.)
    cur.execute(f'DROP TABLE IF EXISTS "{RAW_SCHEMA}"."{table}" CASCADE;')
    cur.execute(f'CREATE TABLE "{RAW_SCHEMA}"."{table}" ({cols_ddl});')

    # Serializa o DataFrame ja limpo de volta para CSV em memoria e usa COPY.
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=True)
    buf.seek(0)

    col_list = ", ".join(f'"{c}"' for c in cols)
    copy_sql = (
        f'COPY "{RAW_SCHEMA}"."{table}" ({col_list}) '
        f"FROM STDIN WITH (FORMAT csv, HEADER true)"
    )
    cur.copy_expert(copy_sql, buf)


def main() -> int:
    if not RAW_DIR.exists():
        print(f"[ERRO] Pasta de dados nao encontrada: {RAW_DIR}")
        print("Coloque os CSVs do Olist em data/raw/ e rode de novo.")
        return 1

    missing = [f for f in CSV_TO_TABLE if not (RAW_DIR / f).exists()]
    if missing:
        print("[ERRO] Faltam CSVs em data/raw/:")
        for f in missing:
            print(f"  - {f}")
        print("\nBaixe o dataset do Kaggle (Brazilian E-Commerce Public Dataset by Olist).")
        return 1

    t0 = time.time()
    conn = connect()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            create_schema(cur)
            for csv_name, table in CSV_TO_TABLE.items():
                path = RAW_DIR / csv_name
                df = read_csv_as_text(path)
                load_table(cur, table, df)
                print(f"[ok] {csv_name:<42} -> {RAW_SCHEMA}.{table:<32} {len(df):>8} linhas")
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"[ERRO] Ingestao falhou e foi revertida: {exc}")
        return 1
    finally:
        conn.close()

    print(f"\nIngestao concluida em {time.time() - t0:.1f}s. Schema: {RAW_SCHEMA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
