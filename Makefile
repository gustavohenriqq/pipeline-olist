# Atalhos do projeto. Use "make <alvo>".
# No Windows, rode os comandos direto (veja o README) ou use "make" via Git Bash / WSL.
#
# Se voce usa um ambiente virtual, aponte o interpretador:
#   make ingest PYTHON=.venv/Scripts/python.exe     (Windows)
#   make ingest PYTHON=.venv/bin/python             (Linux/Mac)
PYTHON ?= python
DBT = $(PYTHON) -m dbt.cli.main

.PHONY: help up down logs ingest freshness reprocessar dbt-run dbt-test dbt-docs ml-testes ml-treinar ml-inferir publicar pipeline clean

help:
	@echo "Alvos disponiveis:"
	@echo "  up         - sobe o Postgres (e pgAdmin) via Docker Compose"
	@echo "  down       - derruba os containers"
	@echo "  ingest     - carrega os CSVs crus no schema raw do Postgres"
	@echo "  freshness  - confere a idade da carga da camada raw (dbt source freshness)"
	@echo "  reprocessar - refaz os fatos so numa janela: make reprocessar INICIO=2018-03-01 FIM=2018-04-01"
	@echo "  dbt-run    - roda os modelos dbt (staging -> intermediate -> marts)"
	@echo "  dbt-test   - roda os testes de qualidade dbt"
	@echo "  dbt-docs   - gera e serve a documentacao dbt em http://localhost:8081"
	@echo "  ml-testes  - testes Python do modelo de atraso (pytest)"
	@echo "  ml-treinar - treina o modelo de atraso e grava ml/artefatos/metricas.json"
	@echo "  ml-inferir - pontua os pedidos e grava marts.previsao_atraso"
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

# Idade da CARGA (coluna _carregado_em da raw), nao do dado de negocio.
freshness:
	cd dbt && $(DBT) source freshness --profiles-dir .

# Substitui nos fatos as linhas com compra entre INICIO (inclusivo) e FIM (exclusivo).
reprocessar:
	cd dbt && $(DBT) build --profiles-dir . --select fato_pedidos fato_itens_pedido --vars "{janela_inicio: '$(INICIO)', janela_fim: '$(FIM)'}"

dbt-run:
	cd dbt && $(DBT) run --profiles-dir .

dbt-test:
	cd dbt && $(DBT) test --profiles-dir .

dbt-docs:
	cd dbt && $(DBT) docs generate --profiles-dir . && $(DBT) docs serve --profiles-dir . --port 8081

# Modelo de atraso (Etapa 4). Ordem: dbt build -> ml-treinar -> ml-inferir
# -> dbt test da source -> publicar. Ver docs/modelo-atraso.md.
ml-testes:
	$(PYTHON) -m pytest tests -q

ml-treinar:
	$(PYTHON) -m ml.treinar

ml-inferir:
	$(PYTHON) -m ml.inferir
	cd dbt && $(DBT) test --profiles-dir . --select source:ml_saida

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
