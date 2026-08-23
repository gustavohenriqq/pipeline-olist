#!/usr/bin/env bash
# Roda o pipeline local fim a fim: Postgres -> ingestao -> dbt build.
# Uso: bash scripts/run_local.sh [--sample] [--publicar]
#
#   --sample     usa data/sample em vez de data/raw (nao precisa do Kaggle)
#   --publicar   ao final, espelha as marts no Neon (precisa do bloco NEON_* no .env)
set -euo pipefail

cd "$(dirname "$0")/.."

PUBLICAR=0
for arg in "$@"; do
  case "$arg" in
    --sample)
      export OLIST_DATA_DIR=data/sample
      echo ">> Usando a amostra (data/sample)"
      ;;
    --publicar)
      PUBLICAR=1
      ;;
    *)
      echo "Argumento desconhecido: $arg" >&2
      exit 1
      ;;
  esac
done

# Permite apontar para o venv do projeto: PYTHON=.venv/Scripts/python.exe bash scripts/run_local.sh
PYTHON="${PYTHON:-python}"

echo ">> Subindo o Postgres..."
docker compose up -d

echo ">> Aguardando o banco ficar pronto..."
sleep 8

echo ">> Ingestao dos CSVs..."
"$PYTHON" ingestion/ingest.py

# dbt build = run + test na ordem certa. Se um teste falha, o que depende dele
# nao roda, entao dado ruim nao avanca pela camada seguinte.
echo ">> Rodando o dbt (build = run + test)..."
(cd dbt && "$PYTHON" -m dbt.cli.main build --profiles-dir .)

if [[ "$PUBLICAR" == "1" ]]; then
  # So chega aqui se o build passou (set -e). Nunca publica dado nao testado.
  echo ">> Publicando as marts no Neon..."
  "$PYTHON" scripts/publicar_marts.py
fi

echo ">> Pronto. Rode 'make dbt-docs' para ver a documentacao e a linhagem."
