"""Gera uma amostra pequena e coerente do dataset Olist.

Por que existir: o dataset completo (~125 MB) nao vai para o Git. Mas e util ter
uma amostra pequena versionada, para o projeto rodar de imediato (e no CI) sem
baixar nada do Kaggle. A amostra preserva as chaves entre tabelas, entao os
testes de integridade do dbt continuam passando.

Uso:
    python scripts/gerar_amostra.py            # 800 pedidos (padrao)
    python scripts/gerar_amostra.py 300        # 300 pedidos
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "sample"


def main(n_orders: int = 800) -> int:
    if not (RAW / "olist_orders_dataset.csv").exists():
        print("[ERRO] data/raw nao tem os CSVs completos. Baixe do Kaggle primeiro.")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    def rd(name):
        return pd.read_csv(RAW / name, dtype=str, keep_default_na=False, encoding="utf-8-sig")

    orders = rd("olist_orders_dataset.csv")
    # Amostra deterministica (seed fixa) para a amostra ser sempre a mesma.
    orders = orders.sample(n=min(n_orders, len(orders)), random_state=42)
    order_ids = set(orders["order_id"])
    customer_ids = set(orders["customer_id"])

    customers = rd("olist_customers_dataset.csv")
    customers = customers[customers["customer_id"].isin(customer_ids)]

    items = rd("olist_order_items_dataset.csv")
    items = items[items["order_id"].isin(order_ids)]
    product_ids = set(items["product_id"])
    seller_ids = set(items["seller_id"])

    payments = rd("olist_order_payments_dataset.csv")
    payments = payments[payments["order_id"].isin(order_ids)]

    reviews = rd("olist_order_reviews_dataset.csv")
    reviews = reviews[reviews["order_id"].isin(order_ids)]

    products = rd("olist_products_dataset.csv")
    products = products[products["product_id"].isin(product_ids)]

    sellers = rd("olist_sellers_dataset.csv")
    sellers = sellers[sellers["seller_id"].isin(seller_ids)]

    zips = set(customers["customer_zip_code_prefix"]) | set(sellers["seller_zip_code_prefix"])
    geo = rd("olist_geolocation_dataset.csv")
    geo = geo[geo["geolocation_zip_code_prefix"].isin(zips)]
    # A raw tem muitas linhas por CEP. Na amostra, uma por prefixo ja basta
    # (o staging faz a media por prefixo de qualquer forma) e deixa o arquivo leve.
    geo = geo.drop_duplicates(subset=["geolocation_zip_code_prefix"])

    translation = rd("product_category_name_translation.csv")

    saidas = {
        "olist_orders_dataset.csv": orders,
        "olist_customers_dataset.csv": customers,
        "olist_order_items_dataset.csv": items,
        "olist_order_payments_dataset.csv": payments,
        "olist_order_reviews_dataset.csv": reviews,
        "olist_products_dataset.csv": products,
        "olist_sellers_dataset.csv": sellers,
        "olist_geolocation_dataset.csv": geo,
        "product_category_name_translation.csv": translation,
    }

    for nome, df in saidas.items():
        df.to_csv(OUT / nome, index=False)
        print(f"[ok] {nome:<42} {len(df):>7} linhas")

    print(f"\nAmostra gerada em {OUT}")
    return 0


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    sys.exit(main(n))
