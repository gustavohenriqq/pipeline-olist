# Atalhos do projeto. Use "make <alvo>".
# No Windows, rode os comandos direto (veja o README) ou use "make" via Git Bash / WSL.

.PHONY: help up down logs ingest dbt-run dbt-test dbt-docs pipeline clean

help:
	@echo "Alvos disponiveis:"
	@echo "  up         - sobe o Postgres (e pgAdmin) via Docker Compose"
	@echo "  down       - derruba os containers"
	@echo "  ingest     - carrega os CSVs crus no schema raw do Postgres"
	@echo "  dbt-run    - roda os modelos dbt (staging -> intermediate -> marts)"
	@echo "  dbt-test   - roda os testes de qualidade dbt"
	@echo "  dbt-docs   - gera e serve a documentacao dbt em http://localhost:8081"
	@echo "  pipeline   - up + ingest + dbt-deps + dbt-run + dbt-test (fim a fim)"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f postgres

ingest:
	python ingestion/ingest.py

dbt-run:
	cd dbt && dbt run --profiles-dir .

dbt-test:
	cd dbt && dbt test --profiles-dir .

dbt-docs:
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir . --port 8081

pipeline: up
	@echo "Aguardando o Postgres ficar pronto..."
	@sleep 8
	python ingestion/ingest.py
	cd dbt && dbt run --profiles-dir . && dbt test --profiles-dir .

clean:
	docker compose down -v
	rm -rf dbt/target dbt/dbt_packages dbt/logs
