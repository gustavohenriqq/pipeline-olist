"""Configuracao central da ingestao.

Le variaveis do arquivo .env (se existir) e expoe a conexao com o Postgres.
Deixar a config num lugar so evita repetir credenciais espalhadas pelo codigo.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz do projeto (uma pasta acima de /ingestion)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Carrega o .env da raiz, se existir. Sem .env, usa os defaults abaixo.
load_dotenv(PROJECT_ROOT / ".env")

# Pasta dos CSVs. Por padrao usa data/raw (dataset completo do Kaggle).
# Pode ser trocada pela variavel OLIST_DATA_DIR (ex: data/sample no CI).
_data_dir_env = os.getenv("OLIST_DATA_DIR")
RAW_DIR = Path(_data_dir_env) if _data_dir_env else (PROJECT_ROOT / "data" / "raw")


def _get(name: str, default: str) -> str:
    return os.getenv(name, default)


PG = {
    "host": _get("POSTGRES_HOST", "localhost"),
    "port": _get("POSTGRES_PORT", "5432"),
    "dbname": _get("POSTGRES_DB", "olist"),
    "user": _get("POSTGRES_USER", "olist"),
    "password": _get("POSTGRES_PASSWORD", "olist"),
}

RAW_SCHEMA = _get("RAW_SCHEMA", "raw")

# Mapeia cada CSV do Kaggle para o nome da tabela no schema raw.
# Nomes curtos e sem o prefixo "olist_" para facilitar as referencias no dbt.
CSV_TO_TABLE = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_name_translation",
}


def sqlalchemy_url() -> str:
    return (
        f"postgresql+psycopg2://{PG['user']}:{PG['password']}"
        f"@{PG['host']}:{PG['port']}/{PG['dbname']}"
    )
