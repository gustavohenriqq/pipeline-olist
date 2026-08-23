"""Publica as tabelas da camada marts do Postgres local para o Neon.

Por que so as marts, e nao o pipeline inteiro?
  - O free tier do Neon da 0.5 GB. So a tabela raw "geolocation" tem ~1 milhao
    de linhas (58 MB de CSV). Subir a raw estoura ou chega perto do limite.
  - Em producao o BI nunca le a camada crua. O Neon aqui e camada de servico:
    guarda so o star schema pronto, que e o que o Looker Studio consome.
  - O warehouse de desenvolvimento continua sendo o Postgres local, onde o dbt
    roda e onde os 57 testes de qualidade rodam antes de qualquer publicacao.

Fluxo: data/raw -> Postgres local -> dbt build -> marts -> [este script] -> Neon.

Como copia: COPY TO STDOUT no local e COPY FROM STDIN no Neon, streamando por
um buffer. Nao carrega a tabela inteira em memoria como um DataFrame faria, e
usa a via nativa de carga em massa dos dois lados.

Uso:
    python scripts/publicar_marts.py            # publica todas as marts
    python scripts/publicar_marts.py fato_pedidos dim_clientes   # so essas
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# Origem: o Postgres local do Docker Compose, onde o dbt materializou as marts.
LOCAL = {
    "host": _get("POSTGRES_HOST", "localhost"),
    "port": _get("POSTGRES_PORT", "5432"),
    "dbname": _get("POSTGRES_DB", "olist"),
    "user": _get("POSTGRES_USER", "olist"),
    "password": _get("POSTGRES_PASSWORD", "olist"),
}
LOCAL_SCHEMA = _get("MARTS_SCHEMA", "marts")

# Destino: Neon. sslmode=require porque o Neon so aceita conexao criptografada.
NEON = {
    "host": _get("NEON_HOST"),
    "port": _get("NEON_PORT", "5432"),
    "dbname": _get("NEON_DB"),
    "user": _get("NEON_USER"),
    "password": _get("NEON_PASSWORD"),
    "sslmode": "require",
}
NEON_SCHEMA = _get("NEON_SCHEMA", "marts")


def listar_marts(cur) -> list[str]:
    """Descobre as tabelas da marts em vez de manter uma lista fixa no codigo.

    Assim, quando uma dimensao nova nascer no dbt, ela e publicada sozinha.
    """
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """,
        (LOCAL_SCHEMA,),
    )
    return [r[0] for r in cur.fetchall()]


def ddl_da_tabela(cur, tabela: str) -> str:
    """Monta o CREATE TABLE do destino espelhando os tipos da origem.

    Le de information_schema em vez de chutar tipos: o que o dbt materializou
    (numeric, timestamp, boolean) chega ao Neon com o mesmo tipo, e o Looker
    Studio ja reconhece data como data e metrica como numero.
    """
    cur.execute(
        """
        SELECT column_name, data_type, character_maximum_length,
               numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (LOCAL_SCHEMA, tabela),
    )
    colunas = []
    for nome, tipo, tam_texto, precisao, escala in cur.fetchall():
        if tipo == "character varying" and tam_texto:
            tipo_final = f"varchar({tam_texto})"
        elif tipo == "numeric" and precisao:
            tipo_final = f"numeric({precisao},{escala or 0})"
        elif tipo == "USER-DEFINED":
            # Tipos customizados nao existem no destino; texto e o seguro.
            tipo_final = "text"
        else:
            tipo_final = tipo
        colunas.append(f'"{nome}" {tipo_final}')

    corpo = ",\n  ".join(colunas)
    return f'CREATE TABLE "{NEON_SCHEMA}"."{tabela}" (\n  {corpo}\n);'


def copiar(cur_origem, cur_destino, tabela: str) -> int:
    """Copia uma tabela inteira via COPY, recriando o destino do zero.

    Recriar (DROP + CREATE) em vez de dar UPDATE e proposital: as marts sao
    reconstruidas inteiras pelo dbt a cada run, entao publicacao incremental
    nao traria ganho e traria risco de divergencia silenciosa entre os dois
    bancos. Carga full mantem o Neon como espelho exato do que foi testado.
    """
    cur_destino.execute(f'DROP TABLE IF EXISTS "{NEON_SCHEMA}"."{tabela}" CASCADE;')
    cur_destino.execute(ddl_da_tabela(cur_origem, tabela))

    buf = io.StringIO()
    cur_origem.copy_expert(
        f'COPY "{LOCAL_SCHEMA}"."{tabela}" TO STDOUT WITH (FORMAT csv, HEADER true)',
        buf,
    )
    buf.seek(0)
    cur_destino.copy_expert(
        f'COPY "{NEON_SCHEMA}"."{tabela}" FROM STDIN WITH (FORMAT csv, HEADER true)',
        buf,
    )

    cur_destino.execute(f'SELECT count(*) FROM "{NEON_SCHEMA}"."{tabela}";')
    return cur_destino.fetchone()[0]


def main() -> int:
    faltando = [k for k in ("host", "dbname", "user", "password") if not NEON[k]]
    if faltando:
        print("[ERRO] Credenciais do Neon ausentes no .env:")
        for k in faltando:
            print(f"  - NEON_{k.upper().replace('DBNAME', 'DB')}")
        print("\nCopie o .env.example para .env e preencha o bloco do Neon.")
        return 1

    t0 = time.time()
    conn_local = psycopg2.connect(**LOCAL)
    conn_neon = psycopg2.connect(**NEON)
    conn_neon.autocommit = False

    try:
        with conn_local.cursor() as cur_local, conn_neon.cursor() as cur_neon:
            disponiveis = listar_marts(cur_local)
            if not disponiveis:
                print(f"[ERRO] Nenhuma tabela em {LOCAL_SCHEMA}. Rode o dbt antes:")
                print("  cd dbt && dbt build --profiles-dir .")
                return 1

            pedidas = sys.argv[1:] or disponiveis
            invalidas = [t for t in pedidas if t not in disponiveis]
            if invalidas:
                print(f"[ERRO] Nao existem em {LOCAL_SCHEMA}: {', '.join(invalidas)}")
                print(f"Disponiveis: {', '.join(disponiveis)}")
                return 1

            cur_neon.execute(f'CREATE SCHEMA IF NOT EXISTS "{NEON_SCHEMA}";')
            for tabela in pedidas:
                linhas = copiar(cur_local, cur_neon, tabela)
                print(f"[ok] {LOCAL_SCHEMA}.{tabela:<24} -> neon:{NEON_SCHEMA}.{tabela:<24} {linhas:>8} linhas")

        conn_neon.commit()
    except Exception as exc:  # noqa: BLE001
        conn_neon.rollback()
        print(f"[ERRO] Publicacao falhou e foi revertida: {exc}")
        return 1
    finally:
        conn_local.close()
        conn_neon.close()

    print(f"\nPublicacao concluida em {time.time() - t0:.1f}s. Destino: {NEON['host']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
