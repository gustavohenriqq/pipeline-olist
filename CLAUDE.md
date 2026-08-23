# CLAUDE.md — Contexto do projeto

Arquivo de contexto para o Claude (e para voce) ao trabalhar neste repo no VS Code / Claude Code. Resume o que e o projeto, o estado atual, como rodar, as convencoes e onde paramos.

## O que e

Pipeline de dados de ponta a ponta sobre o e-commerce brasileiro (dataset publico Olist, ~100 mil pedidos). Vai da ingestao dos CSVs ate um star schema testado, servindo BI (Power BI, Looker Studio) e, mais adiante, um agente de IA em linguagem natural.

- **Dono:** Gustavo Henrique Silva Nascimento (GitHub: gustavohenriqq).
- **Objetivo:** portfolio para vagas de dados (Ambev/Ze Delivery, Radix, dti digital).
- **Repo:** https://github.com/gustavohenriqq/pipeline-olist
- **Projeto irmao (mesmo padrao):** world-cup-2026-data-pipeline.

## Regras da mentoria (seguir sempre)

1. Explicar o porque de cada decisao tecnica, nao so o como.
2. Apresentar alternativas e ajudar a escolher.
3. Alertar sobre o que pode dar problema em producao real.
4. Cada fase termina com um commit e o README atualizado.
5. Se algo nao roda no Databricks Community Edition ou Azure for Students, sugerir alternativa gratuita.
6. Priorizar o que mais aparece nas vagas alvo.
7. Sem em dash (travessao) em nenhum texto gerado.

## Estado atual: Fase 1 concluida, rodada no dataset completo e publicada

Feito e validado no **dataset completo do Kaggle** (99.441 pedidos, 1,5 milhao de linhas na raw): `dbt build` com **88 PASS + 1 WARN + 0 ERROR**, 68 testes de dados.

- Ingestao Python + pandas dos 9 CSVs para o schema `raw` do Postgres (carga via `COPY`, 23s).
- Modelagem dbt: `staging` (views) -> `intermediate` (views) -> `marts` (tables).
- Star schema: `fato_pedidos` (grao de pedido) e `fato_itens_pedido` (grao de item), com `dim_clientes`, `dim_produtos`, `dim_vendedores`, `dim_tempo`, `dim_geolocalizacao`.
- Duas OBTs derivadas para o BI: `obt_pedidos` (grao de pedido) e `obt_itens` (grao de item).
- Camada de servico no **Neon** (Postgres serverless): `scripts/publicar_marts.py` espelha so as marts, 147 MB, 29% do free tier.
- Amostra coerente em `data/sample/` (800 pedidos) versionada, usada pelo CI (GitHub Actions).
- Docker Compose (Postgres + pgAdmin), Makefile, README completo e ROADMAP das 6 fases.

O unico WARN de teste e proposital: 278 CEPs de cliente nao existem na base de geolocalizacao (documentado no README).

**Pendencia unica da Fase 1:** publicar o relatorio no Looker Studio e colar o link no README e em `dashboards/README.md`. O guia de conexao, as paginas sugeridas e os numeros de conferencia ja estao escritos em `dashboards/README.md`.

## Como rodar

Pre requisitos: Docker Desktop e Python 3.11+.

```bash
# opcao rapida, sem baixar o Kaggle (usa data/sample)
docker compose up -d
# no PowerShell use:  $env:OLIST_DATA_DIR="data/sample"; python ingestion/ingest.py
OLIST_DATA_DIR=data/sample python ingestion/ingest.py
cd dbt && dbt build --profiles-dir .

# dataset completo: baixar os 9 CSVs do Olist para data/raw/ e rodar
python ingestion/ingest.py
cd dbt && dbt run --profiles-dir . && dbt test --profiles-dir .
```

Documentacao e linhagem do dbt: `cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir . --port 8081`.

Conexao vem do `.env` (copie de `.env.example`). O `profiles.yml` do dbt le tudo por `env_var`, entao nao ha senha no Git.

## Convencoes importantes

- **Camada raw = tudo TEXT.** Nenhum casting na ingestao. O casting fica no staging (versionado, testavel). O bruto nunca e perdido.
- **Sem `dbt_utils`.** O projeto usa macros proprias para rodar em qualquer ambiente (inclusive sem acesso ao hub do dbt): `gera_sk` (surrogate key md5), `calendario` (date spine), `regiao_br` (UF -> regiao) e testes genericos `combinacao_unica` e `valor_minimo`. Ficam em `dbt/macros/`.
- **Nomes de schema limpos** (`staging`, `intermediate`, `marts`) via macro `generate_schema_name`. Em producao compartilhada, voltar ao padrao `<ambiente>_<schema>` do dbt.
- **Dois fatos, dois graos.** Produto e vendedor so entram no `fato_itens_pedido` (grao de item), porque um pedido tem varios.
- **Cliente = pessoa** (`customer_unique_id`), nao `customer_id` (que muda por pedido).
- Ingestao aceita `OLIST_DATA_DIR` para trocar a pasta de CSVs (o CI usa `data/sample`).
- **Neon recebe so as marts, nunca a raw.** Free tier de 0,5 GB e a `geolocation` crua tem 1 milhao de linhas. Publicar e sempre full e transacional (DROP + CREATE + COPY), e so depois do `dbt build` passar.
- **OBT nao substitui o star schema.** `obt_pedidos` e `obt_itens` existem porque o Looker Studio so junta fontes por blend. Power BI (Fase 4) e o agente (Fase 6) consomem o star, nao as OBTs. Nunca somar metricas das duas OBTs na mesma visao: graos diferentes, receita inflada.

## Ambiente nesta maquina (Windows)

- Python 3.11 nao esta no PATH como `python`; use `py` ou o venv do projeto em `.venv\Scripts\python.exe`.
- O `dbt.exe` e bloqueado pela politica de Controle de Aplicativo do Windows. Rode `\.venv\Scripts\python.exe -m dbt.cli.main <comando>` no lugar.
- CSVs completos do Kaggle ja copiados para `data/raw/` (120 MB, nao versionados).

## Estrutura

```
ingestion/      ingestao Python (config.py, ingest.py)
dbt/            projeto dbt (models/staging|intermediate|marts, macros, tests)
data/raw/       CSVs do Kaggle (NAO versionado; so .gitkeep)
data/sample/    amostra pequena versionada (roda sem Kaggle)
scripts/        gerar_amostra.py, run_local.sh
dashboards/     notas de Looker Studio e Power BI
docs/prints/    prints dos dashboards (a preencher)
.github/workflows/ci.yml   CI: ingest da amostra + dbt build
docker-compose.yml, Makefile, README.md, ROADMAP.md
```

## Onde paramos e o proximo passo

Fase 1 no ar, faltando so publicar o relatorio no Looker Studio. **Depois disso: Fase 2 (cloud/PySpark).**

Plano da Fase 2 (detalhe no ROADMAP.md):
- Camadas Medallion Bronze -> Silver -> Gold em PySpark.
- **Plano B (o Databricks CE nao tem cluster persistente nem mount facil de Blob):**
  - Opcao A (recomendada para comecar): PySpark local, escrevendo Parquet particionado em `data/lake/bronze|silver|gold`.
  - Opcao B: Microsoft Fabric (Lakehouse) via Azure for Students, para ter a nuvem de verdade no portfolio.
  - Opcao C: Azure Blob real + PySpark local lendo via `abfss`.

Cuidados ja mapeados para fases futuras:
- **Fase 6 (agente LangChain):** usuario de banco somente leitura nas marts, bloquear tudo que nao e `SELECT`, `LIMIT` e timeout, e controle de custo de token (modelo barato, so o schema das marts no prompt).

## Dados

Os CSVs completos do Olist nao vao para o Git (pesados). Baixar em https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce e colocar em `data/raw/`. Para so testar, a `data/sample/` ja basta.
