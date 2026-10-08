# Previsão de atraso: plano de implementação

> **Para quem executa:** use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans, tarefa por tarefa. Os passos usam caixas `- [ ]`.

**Objetivo:** prever, no ato da compra, a probabilidade de o pedido atrasar, e gravar a previsão em `marts.previsao_atraso`.

**Arquitetura:** features em SQL num model dbt (`ml.ml_features_atraso`) com lista permitida; pacote Python `ml/` que treina baseline, regressão logística e gradient boosting com separação temporal, escolhe o limiar por custo e grava as previsões numa tabela cujo DDL pertence ao dbt.

**Stack:** dbt-postgres, Python 3.11, pandas, scikit-learn (>=1.4), joblib, pytest.

**Especificação:** [docs/specs/2026-10-08-previsao-atraso-design.md](../specs/2026-10-08-previsao-atraso-design.md)

## Restrições globais

- Janela: compras de 01/01/2017 a 31/08/2018. Treino jan a dez/2017; validação jan a abr/2018; teste mai a ago/2018 (limites: `2017-01-01`, `2018-01-01`, `2018-05-01`, `2018-09-01`, fim exclusivo).
- Custos: ação preventiva R$ 15; atraso não evitado R$ 60. Sensibilidade nas razões 1:2, 1:4, 1:8, com R$ 15 fixo na ação.
- Grade de limiar: 0,01 a 0,99, passo 0,01. Empate: fica o maior limiar (menos alertas).
- `random_state = 42` em tudo.
- PSI: 10 faixas pelos quantis do treino; épsilon 1e-4; sinalizar acima de 0,2.
- Valores de `conjunto`: `treino`, `validacao`, `teste`, `em_andamento`.
- Nenhuma coluna fora de `PERMITIDAS` entra no modelo (teste automático).
- Sem travessão em nenhum texto. Comentários e mensagens em português, sem acento no código (padrão do repositório).
- Comandos dbt nesta máquina: `.venv\Scripts\python.exe -m dbt.cli.main <comando> --profiles-dir .` dentro de `dbt/`.
- Testes Python: `python -m pytest tests -q` a partir da raiz.

## Decisão que ajusta a especificação

A spec diz que a escrita da previsão "apaga e recria" a tabela. Neste plano o **DDL de `marts.previsao_atraso` pertence ao dbt**: um hook `on-run-start` cria a tabela vazia se ela não existir, e `inferir.py` faz `TRUNCATE` + `COPY` numa transação. Motivo: os testes dbt da source rodam dentro de `dbt build`, e falhariam com "relation does not exist" em banco novo (inclusive no CI) se a tabela só nascesse no Python.

## Foco de revisão

1. Categoria ou UF nunca vista no treino aparecendo no teste ou na inferência: deve virar "desconhecida", sem erro. Teste na Tarefa 3.
2. `distancia_km` nula (CEP fora da geolocalização): o modelo principal aceita nulo; a logística imputa a mediana. Teste na Tarefa 3.
3. Mês de backtest sem nenhum atraso (taxa base zero): PR-AUC indefinida deve sair como `None`, sem quebrar o treino. Teste na Tarefa 4.
4. `inferir.py` rodado antes de `treinar.py`: erro com mensagem dizendo para treinar antes. Teste na Tarefa 6.
5. `inferir.py` rodado duas vezes: mesma contagem de linhas, sem duplicar. Verificação na Tarefa 6.

---

### Tarefa 1: features no dbt e tabela de saída

**Arquivos:**
- Criar: `dbt/models/ml/ml_features_atraso.sql`
- Criar: `dbt/models/ml/_ml.yml`
- Criar: `dbt/macros/previsao_atraso.sql`
- Modificar: `dbt/dbt_project.yml` (bloco `ml` em `models`, e `on-run-start`)

**Interfaces:**
- Produz: tabela `ml.ml_features_atraso` com `pedido_sk`, `order_id`, `purchased_at`, `atrasou` (int 0/1, nulo sem entrega) e as colunas de `PERMITIDAS` (Tarefa 3), com os mesmos nomes.
- Produz: tabela vazia `marts.previsao_atraso` com colunas `pedido_sk text, prob_atraso numeric, alerta boolean, conjunto text, limiar numeric, modelo_versao text, gerado_em timestamptz`.

- [ ] **Passo 1: macro `cria_tabela_previsao()` em `dbt/macros/previsao_atraso.sql`**

Retorna SQL com `create schema if not exists marts;` e `create table if not exists marts.previsao_atraso (...)` com as colunas acima. Comentário explicando por que o DDL mora no dbt (ver "Decisão que ajusta a especificação").

- [ ] **Passo 2: `dbt_project.yml`**

Adicionar `on-run-start: ["{{ cria_tabela_previsao() }}"]` e, em `models: olist:`, o bloco `ml: {+materialized: table, +schema: ml}`.

- [ ] **Passo 3: `ml_features_atraso.sql`**

Fontes: `fato_pedidos`, `fato_itens_pedido`, `stg_olist__order_items` (para `seller_id`, `product_id`), `dim_vendedores`, `dim_produtos`, `dim_geolocalizacao`, `stg_olist__customers`, `stg_olist__order_payments`.

Regras:
- Filtro: `purchased_at >= '2017-01-01' and purchased_at < '2018-09-01'` e `order_status not in ('canceled', 'unavailable')`.
- `atrasou`: `case when entregue_no_prazo is null then null when entregue_no_prazo then 0 else 1 end`.
- Vendedor principal e categoria: do item de maior `valor_item` no pedido (desempate por `order_item_id`), com `row_number()`.
- `distancia_km`: haversine entre lat/long do CEP do cliente e do vendedor principal (`dim_geolocalizacao` por `zip_code_prefix`), raio 6371; nulo se faltar um dos lados.
- `tipo_pagamento`: `payment_type` de maior `payment_value` no pedido.
- `frete_sobre_valor`: `valor_frete / nullif(valor_itens, 0)`.
- `mes_compra`, `dia_semana_compra` (`extract(isodow)`), `hora_compra`: inteiros a partir de `purchased_at`.
- `prazo_prometido_dias`: `estimated_delivery_at::date - purchased_at::date`.
- `venda_interregional`: `cliente_regiao <> vendedor_regiao`, texto `'sim'`/`'nao'`.
- Comentário no topo listando as colunas excluídas e o motivo (tabela da seção 4 da spec, resumida).

- [ ] **Passo 4: `_ml.yml`**

Model `ml_features_atraso`: `pedido_sk` unique e not_null; `atrasou` com `accepted_values` [0, 1] (nulos permitidos); `prazo_prometido_dias` not_null.
Source `ml_saida` (schema `marts`), tabela `previsao_atraso`: `pedido_sk` unique e not_null com `relationships` para `ref('fato_pedidos')`; `prob_atraso` com o teste genérico do projeto `valor_minimo` (0) e um teste singular ou `accepted_values` de `conjunto` com os quatro valores. Usar a sintaxe `arguments:` dos testes genéricos (padrão atual do repo).

- [ ] **Passo 5: build e conferência no dataset completo**

Run (em `dbt/`, Postgres local de pé): `..\.venv\Scripts\python.exe -m dbt.cli.main build --profiles-dir .`
Esperado: 0 ERROR; os 3 WARN conhecidos continuam; os testes novos passam (source vazia passa).

Conferir com uma query: linhas de `ml.ml_features_atraso` com `atrasou` não nulo entre jan/2017 e ago/2018 batem com a soma da coluna "n" da seção 2 da spec para esses meses, e a taxa de atraso de mar/2018 é 19,0%.

- [ ] **Passo 6: commit**

```bash
git add dbt/models/ml dbt/macros/previsao_atraso.sql dbt/dbt_project.yml
git commit -m "feat: features de previsao de atraso no dbt e tabela de saida"
```

---

### Tarefa 2: configuração e carga dos dados

**Arquivos:**
- Criar: `ml/__init__.py`, `ml/config.py`, `ml/dados.py`
- Criar: `requirements-ml.txt` (`scikit-learn>=1.4,<1.7`, `numpy>=1.26`, `joblib>=1.3`, `pytest>=8`)
- Modificar: `requirements-extra.txt` (seção de ML vira `-r requirements-ml.txt`)
- Teste: `tests/test_ml_dados.py`

**Interfaces:**
- Produz em `ml/config.py`: `INICIO = date(2017,1,1)`, `FIM_TREINO = date(2018,1,1)`, `FIM_VALIDACAO = date(2018,5,1)`, `FIM = date(2018,9,1)`, `CUSTO_ACAO = 15.0`, `CUSTO_ATRASO = 60.0`, `RAZOES_SENSIBILIDADE = (2, 4, 8)`, `RANDOM_STATE = 42`, `ARTEFATOS: Path` (`ml/artefatos`), `conectar() -> psycopg2 connection` (usa `ingestion.config.PG`, como `scripts/validate_incremental.py`).
- Produz em `ml/dados.py`: `carregar_features(conn) -> pd.DataFrame` (`purchased_at` como datetime); `carregar_atraso_dias(conn) -> pd.DataFrame` (`pedido_sk`, `atraso_dias` de `marts.fato_pedidos`, só para o experimento de sanidade); `separar(df) -> dict[str, pd.DataFrame]` com chaves `treino`, `validacao`, `teste`, `em_andamento`.

- [ ] **Passo 1: testes em `tests/test_ml_dados.py`**

Com um DataFrame sintético cobrindo 2016-12, 2017-06, 2018-02, 2018-06 e um pedido com `atrasou` nulo:
- `test_separar_cortes_sem_sobreposicao`: `treino` só tem compras em [2017-01-01, 2018-01-01); `validacao` em [2018-01-01, 2018-05-01); `teste` em [2018-05-01, 2018-09-01); interseção de `pedido_sk` entre os três é vazia.
- `test_separar_exclui_2016`: nenhuma linha de 2016 em nenhum conjunto.
- `test_em_andamento_sao_os_sem_resposta`: `em_andamento` contém exatamente as linhas com `atrasou` nulo da janela, e elas não aparecem nos outros três.

- [ ] **Passo 2: rodar e ver falhar**

Run: `python -m pytest tests/test_ml_dados.py -q` → falha por import.

- [ ] **Passo 3: implementar `ml/config.py` e `ml/dados.py`** conforme a Interface.

- [ ] **Passo 4: rodar e ver passar**

Run: `python -m pytest tests/test_ml_dados.py -q` → 3 passed.

- [ ] **Passo 5: commit**

```bash
git add ml/__init__.py ml/config.py ml/dados.py requirements-ml.txt requirements-extra.txt tests/test_ml_dados.py
git commit -m "feat: configuracao e separacao temporal dos dados de ML"
```

---

### Tarefa 3: lista permitida e pré-processamento

**Arquivos:**
- Criar: `ml/features.py`
- Teste: `tests/test_ml_features.py`

**Interfaces:**
- Consome: nomes de coluna da Tarefa 1.
- Produz:
  - `NUMERICAS = ("prazo_prometido_dias", "distancia_km", "valor_itens", "valor_frete", "frete_sobre_valor", "qtd_itens", "qtd_vendedores_distintos", "qtd_produtos_distintos", "peso_total_g", "volume_total_cm3", "max_parcelas", "mes_compra", "dia_semana_compra", "hora_compra")`
  - `CATEGORICAS = ("cliente_uf", "cliente_regiao", "vendedor_uf", "vendedor_regiao", "venda_interregional", "categoria_grupo", "tipo_pagamento")`
  - `PERMITIDAS = NUMERICAS + CATEGORICAS`; `ALVO = "atrasou"`
  - `PROIBIDAS = ("approved_at", "delivered_carrier_at", "dias_ate_transportadora", "delivered_customer_at", "tempo_entrega_dias", "dias_em_transporte", "atraso_dias", "entregue_no_prazo", "nota_avaliacao", "order_status", "status_pedido", "situacao_pedido", "valor_pago", "qtd_pagamentos", "ano_compra")`
  - `matriz(df) -> pd.DataFrame`: só as colunas de `PERMITIDAS`, na ordem; `ValueError` listando as que faltarem.
  - `modelo_logistica() -> Pipeline`: numéricas com `SimpleImputer(median)` + `StandardScaler`; categóricas com `SimpleImputer(constant, "desconhecido")` + `OneHotEncoder(handle_unknown="ignore")`; `LogisticRegression(max_iter=1000, random_state=42)`.
  - `modelo_principal(**params) -> Pipeline`: categóricas com `OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1, encoded_missing_value=-1)`, numéricas passadas como estão; `HistGradientBoostingClassifier(categorical_features=<máscara das categóricas>, max_iter=300, random_state=42, **params)`.
  - `versao_features() -> str`: primeiros 8 caracteres do sha1 de `",".join(PERMITIDAS)`.

- [ ] **Passo 1: testes**

- `test_permitidas_e_proibidas_nao_se_cruzam`: `set(PERMITIDAS) & set(PROIBIDAS) == set()`.
- `test_matriz_descarta_colunas_extras`: DataFrame com `PERMITIDAS` + `atraso_dias` + `pedido_sk` → `list(matriz(df).columns) == list(PERMITIDAS)`.
- `test_matriz_acusa_coluna_faltando`: sem `distancia_km` → `ValueError` com "distancia_km" na mensagem.
- `test_modelos_aceitam_categoria_nova_e_nulos`: treina `modelo_logistica()` e `modelo_principal()` em 200 linhas sintéticas com as duas classes; prevê em linhas com `cliente_uf="ZZ"` e `distancia_km=NaN`; `predict_proba` retorna valores em [0, 1] sem erro.

- [ ] **Passo 2: rodar e ver falhar**

Run: `python -m pytest tests/test_ml_features.py -q` → falha por import.

- [ ] **Passo 3: implementar `ml/features.py`** conforme a Interface.

- [ ] **Passo 4: rodar e ver passar** → 4 passed.

- [ ] **Passo 5: commit**

```bash
git add ml/features.py tests/test_ml_features.py
git commit -m "feat: lista permitida de features e pre-processamento dos modelos"
```

---

### Tarefa 4: avaliação, custo, limiar e PSI

**Arquivos:**
- Criar: `ml/avaliacao.py`
- Teste: `tests/test_ml_avaliacao.py`

**Interfaces:**
- Produz:
  - `custo(y, alerta, custo_acao, custo_atraso) -> float` = `custo_acao * alertas + custo_atraso * (atrasos sem alerta)`.
  - `escolher_limiar(y, prob, custo_acao, custo_atraso) -> float`: grade 0,01 a 0,99; menor custo; empate fica o maior limiar.
  - `metricas(y, prob, limiar, custo_acao, custo_atraso) -> dict` com `n`, `taxa_base`, `pr_auc`, `roc_auc`, `brier`, `precisao`, `recall`, `alertas_por_mil`, `custo`, `custo_nunca`, `custo_sempre`. `pr_auc` e `roc_auc` saem `None` quando `y` tem uma classe só.
  - `sensibilidade(y_val, p_val, y_teste, p_teste, razoes, custo_acao) -> list[dict]`: para cada razão r, custo de atraso = `custo_acao * r`; limiar escolhido na validação; retorna `razao`, `limiar`, `custo_teste`, `custo_nunca`, `custo_sempre`.
  - `calibracao(y, prob, faixas=10) -> list[dict]`: por decil de `prob`: `prob_media`, `taxa_real`, `n`.
  - `psi(referencia: pd.Series, atual: pd.Series, faixas=10) -> float`: numérica por quantis da referência (bordas únicas, extremos abertos); categórica por categoria; nulos como categoria própria; proporções com piso 1e-4.

- [ ] **Passo 1: testes**

- `test_custo_conta_alertas_e_atrasos_perdidos`: y=[1,0,1,0], alerta=[1,1,0,0], custos 15/60 → 2×15 + 1×60 = 90.
- `test_limiar_separacao_perfeita`: y=[0,0,1,1], prob=[0.1,0.2,0.8,0.9] → custo zero de atraso; limiar escolhido entre 0,21 e 0,80 e, pelo desempate, igual a 0,80.
- `test_limiar_quando_acao_e_cara_nao_alerta`: y=[0,1], prob=[0.3,0.6], custo_acao=100, custo_atraso=1 → nenhum limiar acima de 0,60 alerta (custo 1), e pelo desempate o escolhido é 0,99.
- `test_metricas_sem_positivos_nao_quebra`: y todo zero → `pr_auc is None`, `roc_auc is None`, `custo_nunca == 0`.
- `test_psi_mesma_distribuicao_proximo_de_zero`: duas amostras da mesma normal (seed 42, n=5000) → `psi < 0.02`.
- `test_psi_distribuicao_deslocada_acima_de_02`: normal(0,1) contra normal(1,1) → `psi > 0.2`.
- `test_psi_categorica`: referência 50/50 "a"/"b", atual 90/10 → `psi > 0.2`.

- [ ] **Passo 2: rodar e ver falhar** → import.

- [ ] **Passo 3: implementar `ml/avaliacao.py`** com `sklearn.metrics` (`average_precision_score`, `roc_auc_score`, `brier_score_loss`).

- [ ] **Passo 4: rodar e ver passar** → 7 passed.

- [ ] **Passo 5: commit**

```bash
git add ml/avaliacao.py tests/test_ml_avaliacao.py
git commit -m "feat: metricas, custo, escolha de limiar e PSI"
```

---

### Tarefa 5: treino, backtest e artefatos

**Arquivos:**
- Criar: `ml/treinar.py`
- Modificar: `.gitignore` (`ml/artefatos/*.joblib`)
- Teste: `tests/test_ml_treinar.py`

**Interfaces:**
- Consome: `separar`, `carregar_features`, `carregar_atraso_dias` (Tarefa 2); `matriz`, `modelo_logistica`, `modelo_principal`, `ALVO`, `versao_features` (Tarefa 3); tudo da Tarefa 4.
- Produz:
  - `ajustar_baseline(treino) -> tuple[dict[str, float], float]`: taxa de atraso por `cliente_uf` e taxa geral.
  - `prever_baseline(tabela, geral, df) -> np.ndarray`: UF ausente recebe `geral`.
  - `GRADE = [{"learning_rate": lr, "max_depth": d, "min_samples_leaf": m} for lr in (0.05, 0.1) for d in (3, 6, None) for m in (20, 100)]`
  - `executar(conjuntos, atraso_dias=None) -> dict` com chaves `limiar`, `params`, `modelo_final` (Pipeline treinado em treino+validação), `relatorio` (dict serializável: métricas de validação e teste dos três modelos, `sensibilidade`, `calibracao` do teste, `backtest`, `drift`, `sanidade` ou `None`, `n` por conjunto, `versao`). `versao` = `f"{date.today():%Y%m%d}-{versao_features()}"`, que vira `modelo_versao` na tabela de saída.
  - CLI `python -m ml.treinar`: conecta, carrega, `executar`, grava `ARTEFATOS/modelo.joblib` (`{"modelo", "limiar", "versao"}`) e `ARTEFATOS/metricas.json` (relatório, indentado, `ensure_ascii=False`), e imprime um resumo.

Regras de `executar`:
1. Baseline e logística ajustadas no treino.
2. Para cada params da `GRADE`, `modelo_principal` no treino; fica o de maior PR-AUC na validação.
3. Limiar: `escolher_limiar` na validação com o principal treinado só no treino.
4. Métricas de validação e teste dos três modelos no limiar de cada um (baseline e logística também escolhem limiar na validação).
5. `sensibilidade` com o principal (validação e teste).
6. Backtest: para cada mês de 2018-01 a 2018-08, principal com os params escolhidos, treinado em todos os rotulados com compra anterior ao mês; reporta `mes`, `n`, `taxa_base`, `pr_auc`.
7. Drift: `psi` de cada coluna de `PERMITIDAS`, treino contra teste e treino contra `em_andamento`; marca `alerta_drift = psi > 0.2`.
8. Sanidade (se `atraso_dias` foi passado): principal com os mesmos params mais a coluna `atraso_dias`, treino → validação; guarda só `roc_auc` e `pr_auc`.
9. `modelo_final`: principal com os params escolhidos treinado em treino+validação.

- [ ] **Passo 1: testes**

- `test_baseline_uf_desconhecida_usa_taxa_geral`: treino com SP 10% e RJ 20% → prever "ZZ" devolve a taxa geral.
- `test_executar_fumaca`: conjuntos sintéticos (treino 600, validação 300, teste 300, em_andamento 50, ~10% positivos, sinal em `prazo_prometido_dias`) com datas em 2017 e em jan e fev/2018 → relatório com as chaves listadas, `0.01 <= limiar <= 0.99`, `len(relatorio["backtest"]) >= 1` e `json.dumps(relatorio)` sem erro.

Para o teste de fumaça ficar rápido, `executar` aceita `grade=None` (usa `GRADE`) e o teste passa `grade=[{"learning_rate": 0.1, "max_depth": 3, "min_samples_leaf": 20}]`.

- [ ] **Passo 2: rodar e ver falhar** → import.

- [ ] **Passo 3: implementar `ml/treinar.py`** conforme a Interface e as regras.

- [ ] **Passo 4: rodar e ver passar** → 2 passed; `python -m pytest tests -q` com tudo verde.

- [ ] **Passo 5: treino real**

Run: `.venv\Scripts\python.exe -m ml.treinar`
Esperado: `ml/artefatos/modelo.joblib` e `ml/artefatos/metricas.json` criados; o resumo mostra `n` de treino perto de 42 mil e de teste perto de 25 mil (soma dos meses na seção 2 da spec), a sanidade com ROC-AUC acima de 0,95, e o PSI de `prazo_prometido_dias` em treino contra `em_andamento`. Registrar os números para a Tarefa 7; não arredondar nem estimar.

- [ ] **Passo 6: commit** (com `metricas.json`, sem o `.joblib`)

```bash
git add ml/treinar.py tests/test_ml_treinar.py .gitignore ml/artefatos/metricas.json
git commit -m "feat: treino com baseline, logistica e gradient boosting, backtest e drift"
```

---

### Tarefa 6: inferência e escrita em `marts.previsao_atraso`

**Arquivos:**
- Criar: `ml/inferir.py`
- Teste: `tests/test_ml_inferir.py`

**Interfaces:**
- Consome: `ARTEFATOS`, `conectar`, `FIM_TREINO`, `FIM_VALIDACAO` (Tarefa 2); `matriz` (Tarefa 3); `modelo.joblib` (Tarefa 5).
- Produz:
  - `carregar_modelo(caminho) -> dict`: `FileNotFoundError` com a mensagem "Modelo nao encontrado. Rode antes: python -m ml.treinar".
  - `atribuir_conjunto(df) -> pd.Series`: `em_andamento` quando `atrasou` é nulo; senão `treino`, `validacao` ou `teste` pelos cortes de data.
  - `montar_saida(df, prob, limiar, versao, gerado_em) -> pd.DataFrame` com as 7 colunas da Tarefa 1, na ordem; `alerta = prob >= limiar`.
  - `gravar(conn, saida) -> int`: numa transação, `TRUNCATE marts.previsao_atraso` + `COPY` a partir de CSV em memória; devolve linhas gravadas.
  - CLI `python -m ml.inferir`.

- [ ] **Passo 1: testes**

- `test_carregar_modelo_ausente_explica_o_que_fazer`: caminho inexistente → `FileNotFoundError` contendo "python -m ml.treinar".
- `test_atribuir_conjunto`: quatro linhas (2017-06 com resposta, 2018-02 com resposta, 2018-07 com resposta, 2018-07 sem resposta) → `["treino", "validacao", "teste", "em_andamento"]`.
- `test_montar_saida_alerta_no_limiar`: prob [0.19, 0.20, 0.21], limiar 0.20 → alerta [False, True, True]; colunas na ordem da Tarefa 1.

- [ ] **Passo 2: rodar e ver falhar** → import.

- [ ] **Passo 3: implementar `ml/inferir.py`.**

- [ ] **Passo 4: rodar e ver passar** → 3 passed.

- [ ] **Passo 5: inferência real e idempotência**

Run duas vezes: `.venv\Scripts\python.exe -m ml.inferir`
Esperado: as duas execuções gravam o mesmo número de linhas, igual a `select count(*) from ml.ml_features_atraso`.

Run (em `dbt/`): `..\.venv\Scripts\python.exe -m dbt.cli.main test --profiles-dir . --select source:ml_saida`
Esperado: todos os testes da source passam.

- [ ] **Passo 6: commit**

```bash
git add ml/inferir.py tests/test_ml_inferir.py
git commit -m "feat: inferencia em lote gravada em marts.previsao_atraso"
```

---

### Tarefa 7: CI, Makefile, documentação e publicação

**Arquivos:**
- Modificar: `.github/workflows/ci.yml` (instalar `requirements-ml.txt`; passo `python -m pytest tests -q` antes do dbt)
- Modificar: `Makefile` (`ml-treinar`, `ml-inferir`)
- Criar: `docs/modelo-atraso.md`
- Modificar: `README.md` (seção curta do modelo com link), `ROADMAP.md` (Etapa 4 concluída, com o que ficou de fora)

- [ ] **Passo 1: CI e Makefile.** Rodar `python -m pytest tests -q` localmente: tudo verde.

- [ ] **Passo 2: `docs/modelo-atraso.md`**

Seções: pergunta e uso; auditoria de features (tabela da spec, seção 4); separação temporal e por quê; resultados (validação e teste dos três modelos); limiar e custo, com a hipótese em destaque e a tabela de sensibilidade; calibração; backtest mensal; drift; experimento de sanidade; limites e próximos passos (seção 12 da spec). **Todos os números vêm de `ml/artefatos/metricas.json`.** Se o modelo principal não superar a baseline no teste, o documento diz isso e explica com o backtest e o drift.

- [ ] **Passo 3: publicar no Neon**

Run: `.venv\Scripts\python.exe scripts\publicar_marts.py`
Esperado: a lista publicada inclui `marts.previsao_atraso` com a mesma contagem da Tarefa 6.

- [ ] **Passo 4: conferir o CI depois do push**

O CI roda o `dbt build` na amostra (inclui o model de features e os testes da source vazia) e o pytest.

- [ ] **Passo 5: commit e push**

```bash
git add .github/workflows/ci.yml Makefile docs/modelo-atraso.md README.md ROADMAP.md
git commit -m "docs: resultados do modelo de previsao de atraso e CI com testes de ML"
git push origin main
```
