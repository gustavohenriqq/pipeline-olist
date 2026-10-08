# Etapa 3: confiabilidade do lado do dbt (o que falta)

Especificação de desenho. Data: 08/10/2026. Estado: desenho aprovado em conversa;
aguardando revisão deste documento.

## 1. Objetivo

Terminar a Etapa 3: tornar a transformação honesta sobre a idade do dado,
rastreável e barata de testar. Os incrementais e a idempotência já foram
entregues (PR #2, [docs/incrementalidade.md](../incrementalidade.md)). Faltam
quatro itens:

1. Freshness da carga da camada raw.
2. Metadados de execução persistidos, visíveis no dashboard.
3. Reprocessamento de uma janela de datas por `--vars`.
4. CI enxuto.

**Critérios de sucesso:**

1. `dbt source freshness` passa logo depois da ingestão e acusa aviso e erro
   pelos limites declarados; o CI roda o comando.
2. Cada `dbt build`, `run` e `test` deixa uma linha em `meta.execucoes_dbt` e uma
   linha por nó em `meta.resultados_dbt`; o `validate_incremental.py` verifica isso.
3. `marts.atualizacao_dados` existe no Postgres local e no Neon, e o rodapé do
   dashboard mostra quando o dado foi processado e o resultado dos testes.
4. Um build com janela substitui só as linhas daquele período, reflete exclusão
   na origem dentro da janela, ignora alteração fora dela e termina igual a um
   full-refresh depois de um build completo; o `validate_incremental.py` prova os
   três pontos.
5. Cada PR roda o CI uma vez; PR que não toca o dbt não reconstrói nenhum model.
6. `docs/confiabilidade.md` explica cada item, o porquê e o que pode dar errado em
   produção; README e ROADMAP marcam a Etapa 3 como concluída.

Restrições que continuam valendo: sem Airflow, sem pacotes do hub do dbt, sem
ferramenta nova. Nenhum travessão em texto.

## 2. Freshness da carga

**O problema.** O dado do Olist é estático (2016 a 2018). Freshness sobre a data
da compra daria erro para sempre e não diria nada. O que pode envelhecer é a
**carga**: quando a ingestão rodou pela última vez. Hoje a raw não guarda isso.

**Desenho.**

- `ingestion/ingest.py` cria cada tabela raw com uma coluna a mais,
  `_carregado_em timestamptz not null default now()`. O `COPY` continua com a
  lista explícita das colunas do CSV, então a coluna recebe o default: a hora da
  transação de carga, igual para todas as linhas da tabela.
- É a única exceção à regra "raw é tudo TEXT", e fica documentada no próprio
  `ingest.py`: é metadado da carga, não dado da origem. Os models de staging
  selecionam colunas explicitamente e não a propagam.
- Em `_olist__sources.yml`, a source `raw` declara `loaded_at_field:
  _carregado_em` e freshness com aviso depois de 24 horas e erro depois de 7
  dias, válida para as 8 tabelas.
- Os limites são ilustrativos: a fonte não é atualizada. Em produção eles
  seguiriam o SLA da carga (por exemplo, aviso se a carga diária atrasar 2 horas).
- CI: passo `dbt source freshness` logo depois da ingestão. Makefile: alvo
  `freshness`.

**Descartado:** freshness sobre `order_purchase_timestamp` (erro permanente, sem
informação) e tabela separada de log de cargas (duplicaria o que a coluna dá de
graça, e o dbt lê a coluna nativamente).

## 3. Metadados de execução

**Desenho.** Dois hooks em `dbt_project.yml`, com macros em
`dbt/macros/metadados.sql`:

- `on-run-start` cria, se não existirem, o schema `meta` e duas tabelas. É o
  mesmo padrão de `cria_tabela_previsao()`.
- `on-run-end` insere uma linha por invocação e uma por nó, lendo o objeto
  `results` do dbt.

`meta.execucoes_dbt`, uma linha por invocação:

| Coluna | Conteúdo |
|---|---|
| `invocation_id` | id da invocação (chave) |
| `comando` | `build`, `run`, `test`, `source freshness` etc. (`flags.WHICH`) |
| `iniciado_em`, `terminado_em` | `run_started_at` e a hora do `on-run-end` |
| `alvo` | `target.name` |
| `versao_dbt` | `dbt_version` |
| `nos`, `sucesso`, `aviso`, `erro`, `pulados` | contagens a partir de `results` |

`meta.resultados_dbt`, uma linha por nó executado:

| Coluna | Conteúdo |
|---|---|
| `invocation_id` | liga à execução |
| `unique_id`, `tipo`, `nome` | identificação do nó (`model`, `test`, `source` etc.) |
| `status` | `success`, `pass`, `warn`, `error`, `fail`, `skipped` |
| `falhas` | linhas que falharam (testes) |
| `segundos` | tempo de execução |
| `mensagem` | mensagem do dbt, truncada em 500 caracteres |

**`marts.atualizacao_dados`.** Uma linha só, reescrita pelo `on-run-end` apenas
quando o comando é `build`. Mora em `marts` para o publicador levá-la ao Neon sem
mudança no script (ele já descobre as tabelas do schema).

| Coluna | Conteúdo |
|---|---|
| `processado_em` | fim do último `dbt build` |
| `carga_raw_em` | maior `_carregado_em` entre as tabelas raw |
| `testes_ok`, `testes_aviso`, `testes_erro` | contagens dos testes desse build |
| `resumo` | texto pronto: "Dados processados em 08/10/2026 15:23 (Brasília) · 104 testes ok, 3 avisos" |

O texto é montado no SQL, no fuso `America/Sao_Paulo`, porque o Looker não
formata bem data e hora vindas do Postgres e o rodapé é texto.

**Looker.** O rodapé da Página 1 ganha um componente lendo `atualizacao_dados`
(nova fonte de dados no Neon, mesma conexão). Ajuste manual pelo Chrome, como na
Etapa 1, registrado em `dashboards/README.md`.

**Testes.** `meta` e `atualizacao_dados` são escritos depois dos testes da
própria execução, então não entram como source testada no build. A verificação
fica no `validate_incremental.py`: depois de cada build no banco descartável, o
número de linhas em `meta.execucoes_dbt` cresce em um, a soma dos nós bate com
`meta.resultados_dbt` daquela invocação, e `atualizacao_dados` tem uma linha.

**Risco aceito.** Se o `on-run-end` falhar, o dbt reporta erro mesmo com os
models construídos. Melhor que um metadado silenciosamente faltando.

**Descartado:** `dbt_artifacts` (pacote do hub, fora da regra do projeto) e
ler `run_results.json` com Python depois do build (mais uma peça para lembrar de
rodar; o hook roda sempre).

## 4. Reprocessamento por janela

**O pedido.** Reprocessar só um período, por exemplo março de 2018, sem comparar
o fato inteiro, e refletir inclusive exclusões na origem dentro dele.

**Desenho.** Duas vars, `janela_inicio` e `janela_fim` (datas, fim exclusivo),
nulas por padrão.

- Sem as vars, os fatos se comportam exatamente como hoje (comparação completa
  com `EXCEPT`).
- Com as vars, num build incremental de `fato_pedidos` e `fato_itens_pedido`:
  - um `pre_hook` apaga do fato as linhas com compra dentro da janela;
  - o model seleciona só os pedidos da janela, sem `EXCEPT`;
  - o `delete+insert` insere essas linhas.
  
  O hook roda na mesma transação do model, então a janela é substituída inteira
  ou não é.
- A janela é pela data da compra: `purchased_at` no `fato_pedidos` e a compra do
  pedido no `fato_itens_pedido`. A data da compra não muda depois do pedido, então
  um registro não migra de janela.
- Uma macro `janela_reprocessamento()` valida as vars: as duas juntas, formato
  `AAAA-MM-DD`, início antes do fim. Caso contrário, `exceptions.raise_compiler_error`
  com a mensagem do uso correto.
- Com `--full-refresh`, as vars são ignoradas (a tabela é reconstruída inteira), e
  o log diz isso.

Uso:

```sh
dbt build --profiles-dir . --select fato_pedidos fato_itens_pedido \
  --vars '{janela_inicio: 2018-03-01, janela_fim: 2018-04-01}'
```

**Validação** (novos cenários no `validate_incremental.py`, banco descartável):

1. Apagar da raw um pedido dentro da janela e alterar um pedido fora dela.
2. Build com a janela: o pedido apagado some dos dois fatos; o alterado fora da
   janela fica como estava; as demais linhas da janela continuam iguais em
   conteúdo.
3. Build normal depois: a alteração fora da janela entra.
4. Full-refresh: igual ao resultado do passo 3 em todas as colunas.

**Descartado:** `incremental_predicates` (restringe o delete às chaves que vieram
no delta, então não remove chaves que sumiram da origem) e uma estratégia
`insert_overwrite` (não existe no dbt-postgres).

## 5. CI enxuto

**Hoje.** O workflow roda em `push` para qualquer branch e em `pull_request`:
cada PR roda duas vezes. Todo push reconstrói o projeto inteiro.

**Desenho.**

- `push` só na `main`; `pull_request` para os PRs. Um PR roda uma vez.
- No PR: checkout com histórico, `git worktree` da branch base em pasta à parte,
  `dbt parse` lá para gerar o manifest da base, e então
  `dbt build --select +state:modified+ --state <manifest da base>`. Antes, `dbt
  ls` com a mesma seleção imprime o que vai rodar.
- Por que `+state:modified+` (com ancestrais) e não `state:modified+ --defer`: o
  banco do CI começa vazio e não existe um ambiente de produção para onde adiar.
  Em produção, com um warehouse de verdade, o certo seria `--defer`, e o doc diz
  isso.
- Se a seleção for vazia (PR só de docs, de ML ou de dashboard), o passo do dbt
  termina sem construir nada. É aí que está o ganho de verdade com este projeto
  pequeno.
- Os passos de ingestão, freshness e pytest continuam no PR.
- O push na `main` mantém o build completo e o `validate_incremental.py`: é a
  rede de segurança depois do merge.

**Risco aceito.** Uma mudança que quebra algo fora da seleção (por exemplo, um
model que depende de uma tabela criada por hook) só aparece no build completo da
`main`. O doc registra isso.

## 6. Documentação

- `docs/confiabilidade.md`: os quatro itens, com o comando, o porquê, os limites e
  o que pode dar errado em produção. O reprocessamento por janela também ganha um
  parágrafo em `docs/incrementalidade.md`, que passa a apontar para o novo doc.
- `dashboards/README.md`: a fonte nova e o componente do rodapé.
- README e ROADMAP: Etapa 3 concluída.

## 7. Arquivos

| Arquivo | Mudança |
|---|---|
| `ingestion/ingest.py` | coluna `_carregado_em` |
| `dbt/models/staging/_olist__sources.yml` | `loaded_at_field` e freshness |
| `dbt/macros/metadados.sql` | DDL do schema `meta` e de `atualizacao_dados`; gravação a partir de `results` |
| `dbt/macros/janela.sql` | `janela_reprocessamento()` e o filtro/hook dos fatos |
| `dbt/models/marts/fato_pedidos.sql`, `fato_itens_pedido.sql` | modo janela |
| `dbt/dbt_project.yml` | hooks e vars |
| `scripts/validate_incremental.py` | cenários de janela e de metadados |
| `.github/workflows/ci.yml` | gatilhos, freshness, seleção por estado no PR |
| `Makefile` | `freshness`, `reprocessar` |
| `docs/confiabilidade.md`, `docs/incrementalidade.md`, `dashboards/README.md`, `README.md`, `ROADMAP.md` | documentação |

## 8. Casos de borda

- Só uma das vars de janela: erro de compilação com o uso correto.
- Janela sem nenhum pedido: o hook apaga zero linhas, o model insere zero, o build
  passa.
- Janela num build que não é incremental (tabela ainda não existe ou
  `--full-refresh`): as vars são ignoradas, com mensagem no log.
- `dbt test` sozinho: grava em `meta`, mas não mexe em `atualizacao_dados` (que
  descreve o último build).
- Comando que falha no meio: o `on-run-end` ainda roda e grava os erros; se o
  próprio hook falhar, o dbt reporta.
- Raw carregada por uma ingestão antiga, sem `_carregado_em`: o freshness falha
  com erro de coluna; a correção é rodar a ingestão de novo (documentado).

## 9. Fora do escopo

- Agendamento e alerta automático de freshness (sem orquestrador, por decisão).
- Ingestão incremental da raw (a fonte é estática).
- Ambiente de produção separado para `--defer`.
- Página de observabilidade no Looker com o histórico de execuções.
