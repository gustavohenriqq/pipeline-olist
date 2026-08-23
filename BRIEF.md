# Projeto — Pipeline de Dados Operacionais · Varejo Brasileiro (Olist)

> Briefing-fonte para mentoria de engenharia de dados. Objetivo: portfólio para aparecer nas vagas de Ambev/Zé Delivery, Radix e dti digital, cobrindo a stack que essas empresas usam.

## Perfil do autor
- Estudante de Ciências da Computação — UNA Sete Lagoas (conclusão Dez/2027).
- Trabalha na AMBEV S.A com Power BI, DAX, Power Query, ETL e SAP no dia a dia.
- Experiência prática: PostgreSQL, SQL analítico, modelagem relacional, dbt (projeto Copa do Mundo 2026 concluído: 6 fontes, modelagem dimensional, dashboard de 11 páginas no Looker Studio).
- GitHub: Workflow (NestJS + React + Docker), CodeSentinel (Java + Spring Boot).
- Ambientes ativos: Azure for Students ($100 crédito), Databricks Community Edition, AWS Treina Brasil.

## Dataset
Brazilian E-Commerce Public Dataset — Olist (Kaggle). ~100k pedidos reais. Tabelas: pedidos, produtos, vendedores, clientes, pagamentos, avaliações, geolocalização. Público, gratuito e reconhecido no mercado BR.

## Arquitetura
```
Olist CSV (Kaggle)
        ↓
Python + pandas (ingestão e limpeza)
        ↓
Azure Blob Storage (Data Lake — camada raw)
        ↓
Databricks + PySpark (transformação em escala)
        ↓
dbt (modelagem dimensional — star schema)
        ↓
PostgreSQL / Azure SQL (data warehouse)
        ↓
┌─────────────┬──────────────┬─────────────┐
Power BI      Looker Studio   Agente IA
(DAX + RLS)   (público)      (LangChain)
```

## Stack por camada
| Camada | Tecnologia |
|---|---|
| Ingestão | Python, pandas |
| Data Lake | Azure Blob Storage |
| Processamento | PySpark no Databricks |
| Transformação | dbt (staging → intermediate → marts) |
| Armazenamento | PostgreSQL local + Azure SQL |
| Orquestração | Apache Airflow com Docker |
| BI principal | Power BI (DAX avançado + RLS + OLS) |
| BI público | Looker Studio |
| IA | Agente LangChain (perguntas em linguagem natural) |
| Versionamento | Git + GitHub |
| Containerização | Docker |

## Fases
1. **Base local (sem. 1-2):** download/exploração Olist, ingestão Python+pandas, carga PostgreSQL local, modelagem dbt (fato_pedidos, dim_clientes, dim_produtos, dim_vendedores, dim_tempo, dim_geolocalizacao), testes dbt + docs, dashboard inicial Looker Studio.
2. **Cloud Azure (sem. 3-4):** Data Lake no Blob Storage, PySpark no Databricks, arquitetura Medallion (Bronze→Silver→Gold), dbt com destino Azure SQL.
3. **Orquestração Airflow (sem. 5):** Airflow via Docker Compose, DAGs de ingestão diária, transformações dbt, atualização do DW, monitoramento e alertas.
4. **Power BI avançado (sem. 6):** dashboard executivo, DAX avançado, RLS por região/vendedor, OLS para métricas sensíveis, relatórios (vendas por região, performance de vendedores, atrasos, ticket médio, NPS).
5. **ML básico (sem. 7):** previsão de demanda com scikit-learn (regressão), feature engineering com pandas, avaliação (RMSE, MAE), resultado no dashboard.
6. **Agente IA (sem. 8):** LangChain respondendo perguntas em linguagem natural sobre os dados, interface Streamlit ou FastAPI, conectado ao PostgreSQL.

## README esperado
Problema de negócio; diagrama de arquitetura; como rodar localmente (Docker Compose); prints Power BI e Looker Studio; link do Looker ao vivo; decisões técnicas e o porquê de cada ferramenta; próximos passos.

## Regras da mentoria
- Explicar o porquê de cada decisão técnica, não só o como.
- Apresentar alternativas e ajudar a escolher.
- Alertar sobre o que pode dar problema em produção real.
- Cada fase = um commit no GitHub com README atualizado.
- Se algo não rodar no Community Edition ou Azure for Students, sugerir alternativa gratuita equivalente.
- Priorizar o que mais aparece nas vagas da Ambev, Radix e dti digital.
