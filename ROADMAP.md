# Roadmap do projeto (6 fases)

Este documento detalha o plano completo. Cada fase termina com um commit e o README atualizado. Para cada fase: o objetivo, as entregas, as decisoes com alternativas, e o que pode dar problema em producao real.

Regra que guia tudo: **priorizar o que mais aparece no mercado de dados**: dbt, SQL, Python, PySpark, Airflow, Azure/AWS, Power BI e modelagem dimensional.

---

## Fase 1 — Base local (concluida)

**Objetivo:** ter o pipeline rodando fim a fim na maquina, com qualidade testada.

**Entregas:**
- Ingestao Python + pandas dos 9 CSVs para o schema `raw` do Postgres (via COPY).
- Projeto dbt: staging, intermediate e marts (star schema).
- 5 dimensoes + 2 fatos + 2 tabelas largas (OBT), 68 testes de qualidade passando.
- Docker Compose com Postgres e pgAdmin.
- Camada de servico no Neon (Postgres serverless) com as marts publicadas.
- Dashboard publico no Looker Studio lendo do Neon.
- README com problema de negocio, arquitetura e decisoes.

**Decisoes e alternativas:**
- **dbt-core (CLI) vs dbt Cloud.** Escolhido o core, gratuito e local. O dbt Cloud tem agendador e IDE web, mas custa e nao agrega para portfolio.
- **PostgreSQL vs DuckDB.** Postgres, porque e o que as vagas pedem e serve BI e agente ao mesmo tempo. DuckDB seria mais rapido para analise local, mas nao e um servidor multiusuario.
- **Publicar so as marts no Neon vs rodar o dbt direto na nuvem.** Escolhido publicar so as marts. O free tier do Neon da 0,5 GB e a raw `geolocation` tem 1 milhao de linhas; alem disso, cada `dbt build` na nuvem viraria trafego de rede. Construir e testar local e publicar so o resultado aprovado e mais rapido, mais barato e espelha o padrao de producao, onde o BI nunca le a camada crua. O target `prod` apontando para o Neon fica documentado no `profiles.yml` como alternativa.
- **Tabela larga (OBT) ao lado do star schema.** O Looker Studio so junta fontes por "blend", que e limitado. Em vez de degradar o modelo, o projeto deriva duas OBTs (`obt_pedidos`, `obt_itens`) a partir do star, que continua sendo a fonte da verdade. Cada OBT respeita um grao, para nao inflar receita.

**Riscos em producao:** schemas fixos, carga full (nao incremental) e geolocalizacao incompleta. Detalhes no README, secao 6. Some-se a isso a duplicacao de dado entre o warehouse local e o Neon: sao dois bancos que podem divergir se alguem publicar sem rodar os testes antes. Por isso a publicacao e sempre full e transacional, e o alvo `make publish` encadeia build e publicacao na ordem certa.

---

## Fase 2 — Cloud na Azure (Data Lake + PySpark)

**Objetivo:** levar o mesmo pipeline para a nuvem, mostrando PySpark e arquitetura Medallion.

**Entregas planejadas:**
- Camada raw (Bronze) no **Azure Blob Storage**.
- Transformacao em **PySpark** (Bronze -> Silver -> Gold).
- dbt com destino no **Azure SQL**.

### Atencao: o Databricks Community Edition tem limites serios

O **Databricks Community Edition (CE)** e gratuito, mas:
- **Nao tem cluster persistente:** o cluster morre depois de um tempo de inatividade e voce perde o estado.
- **Nao tem job scheduler nem API completa:** nao da para orquestrar de fora.
- **Montar o Azure Blob (mount) e chato ou bloqueado:** o CE limita `dbutils.fs.mount` e credenciais.

Ou seja, da para aprender PySpark no CE, mas **nao da para montar uma arquitetura cloud de verdade so com ele.**

### Plano B (recomendado): tres caminhos gratuitos

**Opcao A — PySpark local (mais simples e 100% reproduzivel).**
Rodar PySpark na propria maquina (ou num container Docker), lendo os CSVs e escrevendo Parquet particionado numa pasta que simula o data lake (`data/lake/bronze`, `silver`, `gold`). Vantagem: aprende PySpark e Medallion sem depender de nuvem instavel. Desvantagem: nao mostra o servico Azure em si.

**Opcao B — Microsoft Fabric via Azure for Students (mostra a nuvem de verdade).**
O credito de estudante permite usar **Microsoft Fabric** (Lakehouse + notebooks Spark + OneLake) ou um **Azure Databricks** de avaliacao. Aqui da para ter Blob/OneLake real, Spark gerenciado e integracao com Power BI. Vantagem: e o cenario que as vagas descrevem. Desvantagem: consome credito e exige cuidado para nao estourar.

**Opcao C — Azure Blob real + PySpark local lendo do Blob.**
Meio termo: o data lake fica no Blob Storage (barato), mas o Spark roda local apontando para o Blob via `abfss`. Mostra o servico de storage da nuvem sem depender do cluster do CE.

**Recomendacao de mentoria:** comecar pela **Opcao A** (garante a entrega e o aprendizado de PySpark), e depois, com tempo e credito, subir para a **Opcao B** para ter o print da nuvem no portfolio. Documentar no README qual caminho foi usado e por que.

**Riscos em producao:** custo de cluster ligado sem uso (sempre configurar auto-terminate), e mistura de engines (Spark para volume, dbt para modelagem) que precisa de fronteira clara de responsabilidade.

---

## Fase 3 — Orquestracao com Airflow

**Objetivo:** transformar os passos manuais num pipeline agendado e monitorado.

**Entregas planejadas:**
- Airflow via **Docker Compose**.
- DAG de ingestao diaria -> transformacao dbt -> atualizacao do DW.
- Alertas de falha (email ou webhook) e retries.

**Decisoes e alternativas:**
- **Airflow vs Dagster vs Prefect.** Airflow, porque domina as vagas. Dagster e mais moderno e integra melhor com dbt, vale citar como alternativa. Prefect e mais leve.
- **`BashOperator` chamando dbt vs `astronomer-cosmos`.** Comecar simples com Bash/DockerOperator. O Cosmos renderiza cada model dbt como task no Airflow, otimo, mas adiciona complexidade.

**Riscos em producao:** Airflow local no Docker nao e HA (alta disponibilidade). Em producao usa-se Airflow gerenciado (MWAA na AWS, Composer no GCP) ou Kubernetes. Cuidar tambem de idempotencia: rodar a DAG duas vezes nao pode duplicar dado.

---

## Fase 4 — Power BI avancado

**Objetivo:** dashboard executivo com os recursos que o mercado corporativo cobra de um relatorio serio.

**Entregas planejadas:**
- Dashboard executivo conectado ao DW.
- **DAX avancado:** medidas de receita, ticket medio, % no prazo, NPS aproximado, variacao mes a mes.
- **RLS (Row Level Security)** por regiao e por vendedor.
- **OLS (Object Level Security)** para metricas sensiveis.
- Relatorios: vendas por regiao, performance de vendedores, atrasos, ticket medio, satisfacao.

**Decisoes e alternativas:**
- **Import vs DirectQuery.** Import (dado em memoria) e mais rapido para dashboard; DirectQuery consulta o banco ao vivo, bom para dado que muda toda hora. Para portfolio, Import.
- Como o star schema ja esta pronto no dbt, o Power BI so precisa ligar os relacionamentos. Modelo estrela e exatamente o que o motor VertiPaq do Power BI gosta.

**Riscos em producao:** RLS mal configurado vaza dado entre regioes; sempre testar com "View as role". Modelo sem star schema deixa o Power BI lento.

---

## Fase 5 — ML basico (previsao de demanda)

**Objetivo:** um modelo simples e honesto, bem avaliado.

**Entregas planejadas:**
- Previsao de demanda (pedidos por periodo/categoria) com **scikit-learn (regressao)**.
- Feature engineering com pandas (sazonalidade, mes, regiao, feriado).
- Avaliacao com **RMSE e MAE**, comparando com uma baseline ingenua.
- Resultado levado de volta ao dashboard.

**Decisoes e alternativas:**
- **Regressao simples vs series temporais (Prophet/ARIMA).** Comecar com regressao (scikit-learn basico, honesto no curriculo). Citar Prophet como alternativa para sazonalidade.
- Sempre comparar com baseline (ex: media do mes anterior). Um modelo que nao vence a baseline nao serve.

**Riscos em producao:** vazamento de dado (usar no treino informacao que so existe no futuro), e retreino: modelo envelhece, precisa de reavaliacao periodica.

---

## Fase 6 — Agente de IA (LangChain)

**Objetivo:** responder perguntas de negocio em linguagem natural sobre o DW.

**Entregas planejadas:**
- Agente **LangChain** que traduz pergunta em SQL e responde.
- Interface em **Streamlit** (ou FastAPI).
- Conectado ao PostgreSQL (marts).

### Atencao: dois cuidados que o mentor destacou

**1. SQL injection e seguranca do banco.**
Um agente que gera e executa SQL a partir de texto livre e um risco real. Um usuario pode pedir "apague a tabela de pedidos" e o modelo tentar `DROP TABLE`. Como proteger:

- **Usuario de banco somente leitura.** Criar um role no Postgres com `SELECT` apenas nos schemas `marts`. Mesmo que o modelo gere um `DROP` ou `DELETE`, o banco recusa. Essa e a defesa mais importante.
- **Somente a camada marts.** O agente nao enxerga `raw` nem `staging`.
- **Lista de comandos permitidos.** Bloquear tudo que nao comeca com `SELECT` antes de executar.
- **Limite de linhas e timeout.** Forcar `LIMIT` e um `statement_timeout` curto, para uma pergunta ampla nao travar o banco.
- **Nunca concatenar texto do usuario em SQL na mao.** Deixar o LangChain montar via a toolkit de SQL, com a validacao acima por cima.

**2. Custo de token.**
Cada pergunta manda o schema das tabelas + a pergunta + exemplos para o LLM. Isso custa. Como controlar:

- **Modelo barato por padrao** (ex: `gpt-4o-mini`), subindo de modelo so se precisar.
- **Enviar so o schema das marts**, nao do banco inteiro. Menos tabela no prompt, menos token.
- **Cache de perguntas frequentes**, para nao pagar duas vezes pela mesma coisa.
- **Limite de tentativas.** Se o agente erra o SQL, ele tenta de novo, e cada tentativa custa. Limitar o numero de retries.

**Decisoes e alternativas:**
- **Text-to-SQL (LangChain SQL agent) vs RAG sobre metricas.** Text-to-SQL e mais direto para dado tabular. RAG serviria mais para documentacao. Da para combinar: RAG para explicar as metricas, SQL para calcular.
- **Streamlit vs FastAPI.** Streamlit entrega interface pronta rapido (bom para demo). FastAPI e melhor se virar uma API para outro sistema consumir.

**Riscos em producao:** alem de injection e custo, ha o risco de resposta errada com cara de certa (o modelo inventa numero). Mitigar mostrando o SQL gerado junto da resposta, para a pessoa conferir.

---

## Resumo por prioridade de vaga

| Habilidade da vaga | Fase que cobre |
|---|---|
| dbt / modelagem dimensional | 1 |
| SQL analitico | 1, 4, 6 |
| Python / pandas | 1, 5 |
| PySpark / Databricks | 2 |
| Cloud (Azure / AWS) | 2 |
| Airflow / orquestracao | 3 |
| Power BI (DAX, RLS) | 4 |
| Machine learning | 5 |
| IA / LLM aplicado | 6 |
| Docker | 1, 2, 3 |
