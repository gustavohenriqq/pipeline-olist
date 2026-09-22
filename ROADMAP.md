# Roadmap do projeto

Este documento explica o que o projeto quer responder, como as frentes se
encaixam, e o que foi descartado com a justificativa. Cada etapa termina com um
commit e o README atualizado.

---

## A pergunta que conduz tudo

> **O atraso na entrega destrói a satisfação do cliente. Quanto isso custa, onde
> se concentra, e dá para prever antes de despachar o pedido?**

Não é uma pergunta escolhida por conveniência. Ela saiu dos próprios dados:

| Situação da entrega | Pedidos | Nota média |
|---|---|---|
| No prazo | 89.936 | **4,29** |
| Atraso de 1 a 7 dias | 3.672 | 2,72 |
| Atraso de 8 a 30 dias | 2.517 | **1,65** |
| Atraso acima de 30 dias | 345 | 2,06 |

Atrasar uma semana custa 1,6 ponto de nota. Há **R$ 1,15 milhão em pedidos
atrasados, 7,3% da receita**.

Três frentes atacam a mesma pergunta, e é a conexão entre elas que dá sentido ao
projeto:

| Frente | Papel | Entrega |
|---|---|---|
| **Análise** | Descobrir e quantificar o problema | Documento com recomendação e número |
| **Engenharia** | Entregar o dado com confiabilidade | Models incrementais, idempotência, freshness e CI enxuto |
| **ML** | Agir antes do fato acontecer | Previsão de atraso escrita de volta no warehouse |

O ciclo fecha quando a previsão do modelo aparece no mesmo dashboard que a
análise usou para achar o problema.

---

## Etapa 1 — Fundação (concluída, exceto a publicação do dashboard)

**Objetivo:** ter o pipeline rodando fim a fim, com qualidade testada.

**Entregas:**
- Ingestão Python + pandas dos 9 CSVs para o schema `raw` do Postgres (via COPY).
- Projeto dbt: staging, intermediate e marts (star schema).
- 5 dimensões + 2 fatos + 2 tabelas largas (OBT), 72 testes de qualidade passando.
- Docker Compose com Postgres e pgAdmin.
- Camada de serviço no Neon (Postgres serverless) com as marts publicadas.
- CI no GitHub Actions rodando o pipeline inteiro sobre uma amostra versionada.

**Pendente:** publicar o relatório no Looker Studio e colar o link aqui e no
README. A conexão está pronta e testada, o guia de montagem e os números de
conferência estão em [dashboards/README.md](dashboards/README.md), e existe um
mockup da página inicial em [dashboards/mockup/](dashboards/mockup/). Falta o
passo manual de montar e publicar.

**Decisões e alternativas:**
- **dbt-core (CLI) vs dbt Cloud.** Escolhido o core, gratuito e local. O dbt Cloud tem agendador e IDE web, mas custa e não agrega para portfólio.
- **PostgreSQL vs DuckDB.** Postgres, porque é o que as vagas pedem e serve BI e agente ao mesmo tempo. DuckDB seria mais rápido para análise local, mas não é um servidor multiusuário.
- **Publicar só as marts no Neon vs rodar o dbt direto na nuvem.** Escolhido publicar só as marts. O free tier do Neon dá 0,5 GB e a raw `geolocation` tem 1 milhão de linhas; além disso, cada `dbt build` na nuvem viraria tráfego de rede. Construir e testar local e publicar só o resultado aprovado é mais rápido, mais barato e espelha o padrão de produção, onde o BI nunca lê a camada crua. O target `prod` apontando para o Neon fica documentado no `profiles.yml` como alternativa.
- **Tabela larga (OBT) ao lado do star schema.** O Looker Studio só junta fontes por "blend", que é limitado. Em vez de degradar o modelo, o projeto deriva duas OBTs (`obt_pedidos`, `obt_itens`) a partir do star, que continua sendo a fonte da verdade. Cada OBT respeita um grão, para não inflar receita.

**Riscos em produção:** schemas fixos, carga full (não incremental) e geolocalização incompleta. Detalhes no README, seção 6. Some-se a isso a duplicação de dado entre o warehouse local e o Neon: são dois bancos que podem divergir se alguém publicar sem rodar os testes antes. Por isso a publicação é sempre full e transacional, e o alvo `make publish` encadeia build e publicação na ordem certa.

---

## Etapa 2 — Análise do atraso (concluída)

**Objetivo:** transformar o achado em recomendação defensável, com número.

**Entregue:** [docs/analise-atraso.md](docs/analise-atraso.md).

**Conclusões:**
- O Sudeste concentra 62% dos atrasos mas opera **abaixo** da média nacional (6,1% contra 6,8%). Corrigindo pelo volume, o **Nordeste responde por 537 dos 569 atrasos em excesso do país**, 94% do total.
- **87% do atraso nasce no transporte, 13% no vendedor.** Nos pedidos atrasados do Nordeste o vendedor é o mais rápido do país (4,8 dias contra 6,5 do Sudeste). A ação é logística, não cobrança de SLA de vendedor.
- O efeito do atraso sobre a nota persiste dentro das cinco regiões (queda de 2,55 a 2,74 pontos): não é composição regional.

**A anomalia da cauda, investigada.** A curva não é monótona: acima de 30 dias a
nota sobe para 2,06 contra 1,65 da faixa de 8 a 30. Viés de resposta foi
descartado com número (a taxa de resposta cai apenas 2 pontos). A causa é o dobro
de notas 5 (13,7% contra 6,1%), com z = 5,04 e p = 4,6e-07. A hipótese de
resolução do caso ficou registrada como **não testável**, porque o dataset não
tem atendimento nem reembolso.

**Mudança de modelagem que a análise forçou.** `approved_at` e
`delivered_carrier_at` existiam no staging desde o início, mas nenhuma pergunta
os exigia. Para responder "de quem é o atraso" foram promovidos ao
`fato_pedidos` como `dias_ate_transportadora` e `dias_em_transporte`. Ao
promovê-los, 22 pedidos impossíveis apareceram (transportadora recebendo antes da
compra, cliente antes da transportadora), agora cobertos por teste em aviso.

**O que foi testado e não é viável.** Análise de coorte e retenção, o reflexo
automático em e-commerce: apenas **3,1% dos clientes compraram mais de uma vez**
(93.099 clientes com um único pedido). O dataset não sustenta a análise, e
registrar isso vale mais do que produzir uma coorte sem significado.

**Riscos:** confundir correlação com causa. O atraso acompanha a nota baixa, mas
parte do efeito pode vir de outra coisa (categoria, vendedor, distância). A
análise precisa controlar por esses fatores antes de afirmar causalidade.

---

## Etapa 3 — Confiabilidade do lado do dbt (frente de engenharia)

**Objetivo:** tornar a transformação segura de rodar de novo, barata de testar e
honesta sobre a idade do dado.

**Entregas planejadas:**
- **Models incrementais** nos fatos, com estratégia de merge por chave.
- **Idempotência comprovada:** rodar o build duas vezes não duplica dado, e reprocessar uma janela de datas é um comando (`--vars` com início e fim).
- **Freshness:** `dbt source freshness` com limite de aviso e de erro sobre a camada raw.
- **Metadados de execução persistidos:** resultado de cada build e de cada teste gravado numa tabela, para responder "quando esse número foi atualizado pela última vez?".
- **CI enxuto:** rodar só o que mudou (`state:modified+`), em vez do projeto inteiro a cada push.

**Por que esta etapa importa.** Carga full é a fraqueza que o próprio README já
admite. Idempotência e reprocessamento por janela são o assunto que mais aparece
em entrevista de engenharia de dados, e dá para demonstrá-los inteiramente dentro
do dbt, sem ferramenta nova.

**Decisão: sem Airflow neste projeto.** Orquestração foi retirada daqui de
propósito, e está registrada na tabela de decisões descartadas. O dataset é um
arquivo estático que nunca muda: uma DAG agendada rodaria todo dia sobre o mesmo
dado, e a pergunta "orquestrar o quê?" não teria boa resposta. É o mesmo
raciocínio que tirou o PySpark. Airflow, backfill de fonte viva, data lake
particionado e monitoramento ficam no projeto irmão de transporte público em
tempo real, onde a coleta contínua de uma API cria a necessidade real de cada um.

**Riscos em produção:** model incremental com lógica de janela errada perde ou
duplica dado em silêncio. Por isso o teste de idempotência (build duplo, contagem
igual) entra no CI, e não só na documentação.

---

## Etapa 4 — Previsão de atraso (frente de ML)

**Objetivo:** prever, no momento do pedido, se ele vai atrasar, e devolver isso ao warehouse.

**Entregas planejadas:**
- Classificador binário de atraso, treinado só com informação disponível no ato da compra.
- Baseline ingênua antes do modelo (ex: taxa histórica de atraso por região).
- Split **temporal**, nunca aleatório.
- Limiar de decisão escolhido por custo de negócio, não por 0,5 padrão.
- **Inferência em lote escrita de volta nas marts**, como tabela que o dashboard lê.
- Monitoramento de drift entre treino e produção.

**Por que o alvo mudou.** O plano original era previsão de demanda. Os dados não
sustentam: a série tem **20 meses utilizáveis, ou 1,7 ciclo anual**. Sazonalidade
não se valida com menos de dois ciclos completos, então qualquer padrão que o
modelo encontrasse em novembro seria uma observação isolada, não um padrão. Um
modelo mal fundamentado vale menos que nenhum modelo.

**Por que previsão de atraso funciona aqui:**
- Classe minoritária em **6,8%** dos pedidos entregues: desbalanceado de forma realista, não trivial.
- Há sinal geográfico real: Nordeste **12,7%** de atraso contra Sul **5,9%**.
- Há sinal logístico: venda entre regiões diferentes atrasa **7,5%** contra **6,0%** dentro da mesma região.
- Conecta diretamente com a análise da Etapa 2 e com o dashboard.

**O vazamento que define a qualidade do trabalho.** `tempo_entrega_dias`,
`atraso_dias`, `delivered_customer_at` e `entregue_no_prazo` são informação do
futuro. Um modelo que os usa chega a quase 1,0 de AUC e não serve para nada,
porque no momento do pedido esses campos não existem. O conjunto de features
precisa ser auditado campo a campo, e essa auditoria vai documentada.

**Riscos em produção:** além do vazamento, o retreino. Modelo envelhece e precisa
de reavaliação periódica, senão degrada em silêncio.

---

## Etapa 5 — Power BI avançado

**Objetivo:** dashboard executivo com os recursos que o mercado corporativo cobra de um relatório sério.

**Entregas planejadas:**
- Dashboard executivo conectado ao DW.
- **DAX avançado:** medidas de receita, ticket médio, % no prazo, variação mês a mês.
- **RLS (Row Level Security)** por região e por vendedor.
- **OLS (Object Level Security)** para métricas sensíveis.

**Decisões e alternativas:**
- **Import vs DirectQuery.** Import (dado em memória) é mais rápido para dashboard; DirectQuery consulta o banco ao vivo, bom para dado que muda toda hora. Para portfólio, Import.
- Aqui o consumo é do **star schema**, não das OBTs: o motor VertiPaq foi feito para modelo dimensional.

**Riscos em produção:** RLS mal configurado vaza dado entre regiões; sempre testar com "View as role".

---

## Etapa 6 — Agente de IA (opcional)

**Objetivo:** responder perguntas de negócio em linguagem natural sobre as marts.

Fica por último e é explicitamente opcional. Só faz sentido depois que as três
frentes principais estiverem profundas. Um agente sobre um pipeline raso
impressiona menos que um pipeline sólido sem agente.

**Entregas planejadas:** agente LangChain traduzindo pergunta em SQL, interface
Streamlit, conectado só às marts.

**Dois cuidados obrigatórios:**

**1. Segurança do banco.** Um agente que gera e executa SQL a partir de texto
livre é risco real. Defesas, em ordem de importância:
- **Usuário de banco somente leitura**, com `SELECT` apenas nos schemas `marts`. Mesmo que o modelo gere `DROP`, o banco recusa. Esta é a defesa que importa.
- O agente não enxerga `raw` nem `staging`.
- Bloquear tudo que não começa com `SELECT` antes de executar.
- Forçar `LIMIT` e `statement_timeout` curto.
- Nunca concatenar texto do usuário em SQL na mão.

**2. Custo de token.** Modelo barato por padrão, enviar só o schema das marts,
cache de perguntas frequentes e limite de tentativas.

**Risco principal:** resposta errada com cara de certa. Mitigar mostrando o SQL
gerado junto da resposta. Este projeto já tem evidência do problema: ao gerar o
mockup do dashboard, um modelo inventou os valores de 6 das 9 UFs do mapa e citou
dois estados que nem estão no top 9, acertando apenas os três que receberam
explicitamente no prompt. Modelo de linguagem preenche lacuna com o que parece
razoável. O agente precisa de guarda contra exatamente isso.

---

## Decisões descartadas, e por quê

Registrar o que não foi feito, e a evidência por trás, vale tanto quanto
registrar o que foi.

| Descartado | Evidência | Decisão |
|---|---|---|
| **PySpark / Medallion em Spark** | 99.441 pedidos, 1,5 milhão de linhas na raw. O pipeline inteiro roda em 23s num Postgres em container | Volume não justifica computação distribuída. Usar Spark aqui seria demonstração vazia, e a pergunta "por que Spark?" não teria boa resposta |
| **Previsão de demanda** | 20 meses utilizáveis, 1,7 ciclo anual | Impossível validar sazonalidade com menos de 2 ciclos. Alvo trocado por previsão de atraso |
| **Análise de coorte e retenção** | 3,1% de clientes com mais de um pedido | Dataset não sustenta. Registrado como achado, não produzido como análise vazia |
| **dbt Cloud** | Custa, e o valor é agendador e IDE web | dbt-core cobre o que o projeto precisa |
| **Databricks Community Edition** | Sem cluster persistente, sem scheduler, mount de Blob limitado | Não permite arquitetura cloud de verdade |
| **Airflow** | Fonte é um arquivo estático, sem atualização. Não há evento, agenda nem janela nova para processar | Orquestração sem necessidade real vira enfeite. Coberta no projeto irmão, onde a coleta contínua de API a justifica |

---

## O que este projeto não demonstra

Honestidade sobre limite é parte do trabalho. Este projeto **não** cobre:

- **Ingestão de fonte viva.** É um dump estático de CSV. Sem API, sem schema que muda, sem rate limit, sem fonte que cai.
- **Escala.** 1,5 milhão de linhas cabe na memória de um notebook.
- **Streaming e CDC.** Tudo é batch.
- **Orquestração.** Sem fonte que muda, não há o que agendar.

Essas competências pedem um projeto de forma diferente, com dado coletado ao
longo do tempo de uma fonte real. É a lacuna consciente deste repositório, e é
coberta por um projeto irmão de transporte público em tempo real.

### Divisão de papéis entre os dois projetos

| Projeto | Papel | Competências centrais |
|---|---|---|
| **Este (Olist)** | Analytics engineering, análise e ML | dbt, star schema, testes de qualidade, análise com recomendação, estatística, classificação |
| **Transporte em tempo real** | Engenharia de dados | Ingestão de API, data lake medallion particionado, PySpark, Airflow, monitoramento |

A divisão evita que os dois repitam a mesma demonstração, e cada ferramenta
aparece onde o problema de fato a exige.
