# Atalhos do projeto. Use "make <alvo>".
# No Windows, rode os comandos direto (veja o README) ou use "make" via Git Bash / WSL.
#
# Se voce usa um ambiente virtual, aponte o interpretador:
#   make ingest PYTHON=.venv/Scripts/python.exe     (Windows)
#   make ingest PYTHON=.venv/bin/python             (Linux/Mac)
PYTHON ?= python
DBT = $(PYTHON) -m dbt.cli.main

.PHONY: help up down logs ingest dbt-run dbt-test dbt-docs publicar pipeline clean

help:
	@echo "Alvos disponiveis:"
	@echo "  up         - sobe o Postgres (e pgAdmin) via Docker Compose"
	@echo "  down       - derruba os containers"
	@echo "  ingest     - carrega os CSVs crus no schema raw do Postgres"
	@echo "  dbt-run    - roda os modelos dbt (staging -> intermediate -> marts)"
	@echo "  dbt-test   - roda os testes de qualidade dbt"
	@echo "  dbt-docs   - gera e serve a documentacao dbt em http://localhost:8081"
	@echo "  publicar   - espelha as marts no Neon (camada de servico do BI)"
	@echo "  pipeline   - up + ingest + dbt build (fim a fim, local)"
	@echo "  publish    - pipeline + publicar (fim a fim ate o dashboard)"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f postgres

ingest:
	$(PYTHON) ingestion/ingest.py

dbt-run:
	cd dbt && $(DBT) run --profiles-dir .

dbt-test:
	cd dbt && $(DBT) test --profiles-dir .

dbt-docs:
	cd dbt && $(DBT) docs generate --profiles-dir . && $(DBT) docs serve --profiles-dir . --port 8081

# Publica so a camada marts no Neon. Roda depois do dbt, nunca antes:
# o que vai para o BI e sempre o que ja passou nos testes de qualidade.
publicar:
	$(PYTHON) scripts/publicar_marts.py

pipeline: up
	@echo "Aguardando o Postgres ficar pronto..."
	@sleep 8
	$(PYTHON) ingestion/ingest.py
	cd dbt && $(DBT) build --profiles-dir .

publish: pipeline publicar

clean:
	docker compose down -v
	rm -rf dbt/target dbt/dbt_packages dbt/logs
