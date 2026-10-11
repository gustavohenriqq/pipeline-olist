"""Cria ou atualiza o usuario somente leitura do agente no Neon.

Uso: python scripts/criar_usuario_agente.py
Le NEON_* e AGENTE_DB_PASSWORD do .env. Rode de novo para trocar a senha.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")
sys.path.insert(0, str(RAIZ))

from agente.permissoes import aplicar_permissoes  # noqa: E402


def main() -> int:
    senha = os.getenv("AGENTE_DB_PASSWORD", "")
    if len(senha) < 16:
        print("[ERRO] Defina AGENTE_DB_PASSWORD no .env com 16 ou mais caracteres.")
        return 1
    neon = {
        "host": os.getenv("NEON_HOST"),
        "port": os.getenv("NEON_PORT", "5432"),
        "dbname": os.getenv("NEON_DB"),
        "user": os.getenv("NEON_USER"),
        "password": os.getenv("NEON_PASSWORD"),
        "sslmode": "require",
    }
    if not all(neon[k] for k in ("host", "dbname", "user", "password")):
        print("[ERRO] Credenciais do Neon ausentes no .env (NEON_*).")
        return 1
    conn = psycopg2.connect(**neon)
    try:
        with conn.cursor() as cur:
            tabelas = aplicar_permissoes(cur, senha)
        conn.commit()
    finally:
        conn.close()
    print(f"[ok] agente_leitura com SELECT em: {', '.join(tabelas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
