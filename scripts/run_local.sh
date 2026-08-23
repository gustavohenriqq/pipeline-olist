#!/usr/bin/env bash
# Roda o pipeline local fim a fim: Postgres -> ingestao -> dbt run -> dbt test.
# Uso: bash scripts/run_local.sh [--sample]
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--sample" ]]; then
  export OLIST_DATA_DIR=data/sample
  echo ">> Usando a amostra (data/sample)"
fi

echo ">> Subindo o Postgres..."
docker compose up -d

echo ">> Aguardando o banco ficar pronto..."
sleep 8

echo ">> Ingestao dos CSVs..."
python ingestion/ingest.py

echo ">> Rodando o dbt (run + test)..."
cd dbt
dbt run  --profiles-dir .
dbt test --profiles-dir .

echo ">> Pronto. Rode 'make dbt-docs' para ver a documentacao e a linhagem."
