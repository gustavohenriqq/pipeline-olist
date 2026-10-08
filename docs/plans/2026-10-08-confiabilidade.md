# Etapa 3 (restante): plano de implementação

> **Para quem executa:** use superpowers:executing-plans (ou subagent-driven-development), tarefa por tarefa. Os passos usam caixas `- [ ]`.

**Objetivo:** terminar a Etapa 3 com freshness da carga, metadados de execução visíveis no dashboard, reprocessamento por janela e CI enxuto; antes disso, acentuar os documentos que ficaram sem acento.

**Arquitetura:** tudo dentro do dbt e do CI existentes. A ingestão grava `_carregado_em`; hooks `on-run-start`/`on-run-end` mantêm o schema `meta` e `marts.atualizacao_dados`; os fatos ganham um modo janela por `--vars`; o workflow passa a selecionar por estado no PR. A verificação de banco fica no `scripts/validate_incremental.py`, que roda num banco descartável.

**Stack:** dbt-postgres 1.12, Python 3.11, psycopg2, GitHub Actions.

**Especificação:** [docs/specs/2026-10-08-confiabilidade-design.md](../specs/2026-10-08-confiabilidade-design.md)

## Restrições globais

- Sem Airflow, sem pacotes do hub do dbt, sem ferramenta nova.
- Sem travessão em nenhum texto. Documentos (`.md`) em português **com** acento; código, SQL e comentários **sem** acento (padrão do repositório).
- Comandos dbt nesta máquina: `..\.venv\Scripts\python.exe -m dbt.cli.main <comando> --profiles-dir .` dentro de `dbt/`.
- Rodar Python pesado com `OMP_NUM_THREADS=4`; nunca parar processos que não foram iniciados nesta sessão.
- `validate_incremental.py` precisa do Postgres local de pé (usuário com `CREATEDB`).
- Freshness: aviso depois de 24 horas, erro depois de 7 dias.
- Vars de janela: `janela_inicio`, `janela_fim`, formato `AAAA-MM-DD`, fim exclusivo.
- Fuso do texto do rodapé: `America/Sao_Paulo`.

## Foco de revisão

1. Só uma das vars de janela, data inválida ou início depois do fim: erro de compilação com o uso correto, nunca um build que apaga dado. Verificação na Task 4.
2. Janela num build não incremental (tabela inexistente ou `--full-refresh`): vars ignoradas, sem apagar nada. Verificação na Task 4.
3. Mensagem de erro do dbt com aspas simples gravada em `meta.resultados_dbt`: precisa ser escapada, senão o próprio `on-run-end` quebra. Teste na Task 3.
4. `dbt test` sozinho não pode alterar `marts.atualizacao_dados`. Verificação na Task 3.
5. PR que só muda documentação: o passo do dbt no CI termina sem construir nada. Verificação na Task 5.

---

### Task 1: acentuar os documentos

**Arquivos:**
- Modificar: `README.md`, `dashboards/README.md`, `dashboards/mockup/README.md`, `docs/incrementalidade.md`
- Criar (fora do repo, scratchpad): `confere_acentos.py`

**Regras:** acentuar só o texto em português. Não mexer em blocos de código, código inline, comandos, links, nomes de arquivo, de coluna e de schema. Ler o texto e decidir cada caso ambíguo pelo sentido ("e"/"é", "esta"/"está", "so"/"só", "ate"/"até", "nos"/"nós").

- [ ] **Passo 1: script de conferência** `confere_acentos.py <arquivo_antigo> <arquivo_novo>`: remove acentos do novo (NFD, descarta marcas combinantes, `ç`→`c`) e compara linha a linha com o antigo; imprime as linhas diferentes. Tirar a versão antiga com `git show HEAD:<arquivo>`.
- [ ] **Passo 2: rodar contra os arquivos ainda sem mudança** → 0 linhas diferentes (o script não acusa falso positivo).
- [ ] **Passo 3: acentuar os quatro arquivos.**
- [ ] **Passo 4: conferir** → 0 linhas diferentes em cada arquivo, ou só diferenças intencionais de grafia que não são acento (por exemplo "porque" → "por quê"), listadas no ledger.
- [ ] **Passo 5:** `grep -c` de acentos maior que zero em cada arquivo e nenhum travessão.
- [ ] **Passo 6: commit** `docs: acentuacao do README e dos guias`.

---

### Task 2: freshness da carga

**Arquivos:**
- Modificar: `ingestion/ingest.py` (`load_table`), `dbt/models/staging/_olist__sources.yml`, `Makefile` (alvo `freshness`), `scripts/validate_incremental.py`

**Interfaces:**
- Produz: coluna `_carregado_em timestamptz not null default now()` em todas as tabelas `raw.*` (consumida pela Task 3 para `carga_raw_em`).

- [ ] **Passo 1: cenário de validação primeiro.** Em `validate_incremental.py`, função `check_freshness(database, env)`: roda `dbt source freshness` (espera código 0); depois `update raw.orders set _carregado_em = now() - interval '2 days'` e roda de novo (espera aviso: código 0 e "WARN" na saída); depois `- interval '8 days'` (espera código diferente de 0 e "ERROR"); restaura `now()`. Chamar logo após a ingestão em `main()`.
- [ ] **Passo 2: rodar** `python scripts/validate_incremental.py` → falha (coluna `_carregado_em` não existe).
- [ ] **Passo 3: implementar.** `load_table` cria a tabela com as colunas do CSV mais `"_carregado_em" timestamptz not null default now()`; o `COPY` continua com a lista das colunas do CSV. Comentário explicando a exceção à regra "raw tudo TEXT". Na source `raw`: `loaded_at_field: _carregado_em` e freshness (aviso 24 horas, erro 7 dias), na sintaxe que o dbt 1.12 aceitar sem aviso de depreciação (`config:`). Makefile: `freshness: cd dbt && $(DBT) source freshness --profiles-dir .`
- [ ] **Passo 4: rodar** a validação → passa com as três linhas de freshness. Rodar também a ingestão local completa e `dbt source freshness` → PASS nas 8 tabelas; `dbt build` completo → 0 ERROR.
- [ ] **Passo 5: commit** `feat: freshness da carga da camada raw`.

---

### Task 3: metadados de execução

**Arquivos:**
- Criar: `dbt/macros/metadados.sql`
- Modificar: `dbt/dbt_project.yml` (hooks), `scripts/validate_incremental.py`

**Interfaces:**
- Consome: `_carregado_em` (Task 2).
- Produz: macros `cria_tabelas_metadados()` (DDL de `meta.execucoes_dbt`, `meta.resultados_dbt` e `marts.atualizacao_dados`, todas `create ... if not exists`), `texto_sql(valor, limite=500)` (literal SQL com aspas escapadas, truncado, `null` para vazio) e `grava_metadados(results)` (SQL de insert). Colunas exatamente como nas tabelas da seção 3 da spec.

- [ ] **Passo 1: cenários de validação primeiro.** Função `check_metadados(database, comando_esperado)` chamada depois de cada `build()` em `main()`: `meta.execucoes_dbt` ganhou exatamente uma linha nova; `nos` dessa linha é igual ao `count(*)` de `meta.resultados_dbt` com o mesmo `invocation_id`; `sucesso + aviso + erro + pulados = nos`; `marts.atualizacao_dados` tem uma linha e `resumo` começa com "Dados processados em". Mais dois cenários: (a) rodar `dbt test` e conferir que `atualizacao_dados.processado_em` não mudou e que `execucoes_dbt` ganhou uma linha com `comando = 'test'`; (b) escape: `dbt run-operation testa_texto_sql` (macro em `dbt/macros/metadados.sql`) executa `select {{ texto_sql("it's") }} = 'it''s'` e `select length({{ texto_sql('x' * 600) }}) = 500` e chama `exceptions.raise_compiler_error` se algum for falso; a validação espera código 0.
- [ ] **Passo 2: rodar** a validação → falha (`meta.execucoes_dbt` não existe).
- [ ] **Passo 3: implementar.** `on-run-start` chama `cria_tabelas_metadados()` junto do hook existente; `on-run-end` chama `grava_metadados(results)`. Status por `result.status | string`; tipo por `result.node.resource_type`; mensagem com `replace("'", "''")` e truncada em 500; `comando` por `flags.WHICH`. `atualizacao_dados` só é reescrita (`truncate` + `insert`) quando `flags.WHICH == 'build'`; `carga_raw_em` é o maior `_carregado_em` entre as sources do `graph` com `source_name == 'raw'`; `testes_erro` soma `fail` e `error`; `resumo` = "Dados processados em DD/MM/AAAA HH24:MI (Brasília) · N testes ok, M avisos" (acrescenta ", K erros" se K > 0).
- [ ] **Passo 4: rodar** a validação → passa. `dbt build` local completo e conferir com SQL: uma linha nova em `meta.execucoes_dbt` com `erro = 0`, e as contagens do `resumo` iguais às do resumo impresso pelo próprio `dbt build`.
- [ ] **Passo 5: commit** `feat: metadados de execucao do dbt e tabela de atualizacao`.

---

### Task 4: reprocessamento por janela

**Arquivos:**
- Criar: `dbt/macros/janela.sql`
- Modificar: `dbt/models/marts/fato_pedidos.sql`, `dbt/models/marts/fato_itens_pedido.sql`, `dbt/dbt_project.yml` (vars nulas por padrão), `scripts/validate_incremental.py`, `Makefile` (alvo `reprocessar` com `INICIO` e `FIM`)

**Interfaces:**
- Produz: `janela_reprocessamento()` → `none` sem vars, ou `{"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD"}`; erro de compilação nos casos inválidos. `apaga_janela(coluna_sql)` → `delete from {{ this }} where <coluna> >= inicio and <coluna> < fim` só quando a janela existe e `is_incremental()`; senão string vazia. `fato_pedidos` usa `purchased_at`; `fato_itens_pedido` usa `tempo_sk_compra` comparado com o inteiro `AAAAMMDD`.

- [ ] **Passo 1: cenário de validação primeiro.** Função `check_janela(database, build)` depois dos cenários atuais: escolher um pedido de março/2018 com itens (`alvo`) e um pedido fora de março (`fora`); apagar `alvo` da raw (orders, items, payments, reviews); mudar o status de `fora`; `build("--select", "fato_pedidos", "fato_itens_pedido", "--vars", "{janela_inicio: '2018-03-01', janela_fim: '2018-04-01'}")`; conferir: `alvo` sumiu dos dois fatos, `fora` mantém o status antigo, as outras linhas de março têm o mesmo conteúdo de antes. Depois `build()` normal: `fora` atualizado. Depois `--full-refresh`: igual ao snapshot anterior em todas as colunas. Também: `dbt compile` com só `janela_inicio` → código diferente de 0 e "janela_fim" na saída; com início depois do fim → código diferente de 0.
- [ ] **Passo 2: rodar** → falha (`alvo` continua no fato).
- [ ] **Passo 3: implementar.** Nos fatos: `pre_hook="{{ apaga_janela('purchased_at') }}"` (e o equivalente no de itens); no corpo, com janela e `is_incremental()`, filtrar o resultado pela janela e não aplicar o `EXCEPT`; sem janela, código atual intacto. Com janela e sem incremental: `log` dizendo que as vars foram ignoradas. A janela vale na data da compra, e a de itens usa a data do pedido.
- [ ] **Passo 4: rodar** a validação → passa. `dbt build` local completo sem vars → mesmas contagens de antes nos fatos.
- [ ] **Passo 5: commit** `feat: reprocessamento dos fatos por janela de datas`.

---

### Task 5: CI enxuto

**Arquivos:**
- Modificar: `.github/workflows/ci.yml`

- [ ] **Passo 1: gatilhos.** `push` só em `main`; `pull_request` mantido. Checkout com `fetch-depth: 0`.
- [ ] **Passo 2: freshness** logo depois da ingestão (`dbt source freshness`).
- [ ] **Passo 3: PR.** Passo condicional `github.event_name == 'pull_request'`: `git worktree add "$RUNNER_TEMP/base" "origin/${{ github.base_ref }}"`, `dbt parse --profiles-dir . --target-path "$RUNNER_TEMP/estado_base"` dentro de `$RUNNER_TEMP/base/dbt`; depois, no projeto, `dbt ls --select +state:modified+ --state "$RUNNER_TEMP/estado_base"` e `dbt build` com a mesma seleção. Comentário explicando por que `+` à esquerda e não `--defer`.
- [ ] **Passo 4: main.** Build completo e `validate_incremental.py` só quando `github.event_name == 'push'`.
- [ ] **Passo 5: verificar no GitHub.** O PR desta branch roda uma vez só; o log do `dbt ls` mostra a seleção (esta branch muda os fatos, então a seleção não é vazia). Para provar o caso vazio: abrir um PR de teste, a partir da `main` depois do merge, que só altera um `.md`; o passo do dbt deve mostrar seleção vazia e não construir nada. Fechar esse PR sem merge. Registrar os dois links das execuções no ledger.
- [ ] **Passo 6: commit** `ci: um run por PR, selecao por estado e freshness`.

---

### Task 6: documentação, publicação e dashboard

**Arquivos:**
- Criar: `docs/confiabilidade.md`
- Modificar: `docs/incrementalidade.md` (parágrafo da janela, link), `dashboards/README.md` (fonte nova e rodapé), `README.md`, `ROADMAP.md` (Etapa 3 concluída, título sem travessão), `Makefile` (help)

- [ ] **Passo 1: `docs/confiabilidade.md`** com uma seção por item (freshness, metadados, janela, CI): comando, porquê, limites e o que pode dar errado em produção (os riscos da spec). Números só de execuções reais desta sessão.
- [ ] **Passo 2: publicar no Neon.** `.venv\Scripts\python.exe scripts\publicar_marts.py` → a lista inclui `marts.atualizacao_dados` com 1 linha.
- [ ] **Passo 3: Looker (Chrome).** Adicionar a fonte `atualizacao_dados` (conexão Neon existente) e um componente no rodapé da Página 1 mostrando `resumo`, no estilo do rodapé atual. Conferir no modo de visualização que o texto bate com o banco.
- [ ] **Passo 4: README e ROADMAP.** Etapa 3 concluída, com link para o doc.
- [ ] **Passo 5: commit** `docs: confiabilidade do pipeline e Etapa 3 concluida`; push; PR; CI verde.
