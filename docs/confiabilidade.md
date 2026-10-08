# Confiabilidade do pipeline

Etapa 3. O objetivo é que a transformação seja honesta sobre a idade do dado,
rastreável e barata de testar. Os fatos incrementais e a idempotência vieram
antes e estão em [incrementalidade.md](incrementalidade.md). Este documento cobre
o resto: freshness da carga, metadados de execução, reprocessamento por janela e
CI enxuto. A especificação está em
[docs/specs](specs/2026-10-08-confiabilidade-design.md).

Tudo é verificado pelo `scripts/validate_incremental.py`, num banco descartável
criado com a amostra. Ele roda no CI e imprime uma linha por garantia:

```
OK: freshness passa na carga nova, avisa com 2 dias e falha com 8
OK: build repetido conserva linhas e versoes fisicas
OK: metadados por invocacao; dbt test nao altera o rodape; aspas escapadas
OK: novos registros antigos e correcoes aplicados; demais linhas preservadas
OK: delta idempotente e identico ao full-refresh em todas as colunas dos fatos
OK: janela remove o apagado, ignora o de fora, iguala o full-refresh e rejeita vars invalidas
```

---

## 1. Freshness da carga

```sh
cd dbt && dbt source freshness --profiles-dir .     # ou: make freshness
```

**O que mede.** A idade da **carga**, não do dado de negócio. O Olist é estático
(2016 a 2018): freshness sobre a data da compra daria erro para sempre e não diria
nada. O que pode envelhecer aqui é a ingestão, então ela passou a gravar
`_carregado_em` (hora da transação de carga) em cada tabela raw, e a source `raw`
declara essa coluna como `loaded_at_field`.

**Limites.** Aviso depois de 24 horas, erro depois de 7 dias, nas 9 tabelas raw.
São ilustrativos, porque a fonte não é atualizada. Em produção, seguiriam o SLA da
carga: se a ingestão roda todo dia às 6h, um aviso às 8h já diz que algo travou.

**Exceção à regra da raw.** A raw continua "tudo TEXT", com uma exceção:
`_carregado_em` é `timestamptz`, porque é metadado da ingestão e não dado da
origem. Os models de staging selecionam colunas explicitamente e não a propagam.

**Raw antiga.** Uma raw carregada antes dessa mudança não tem a coluna. O
freshness falha com erro de coluna, e o `dbt build` também: os models são
construídos, mas o hook de metadados quebra ao ler `_carregado_em` e o comando
termina com erro. A correção é rodar a ingestão de novo.

**O que pode dar errado em produção.** Freshness verde não quer dizer dado certo:
uma carga que roda no horário mas traz o arquivo de ontem passa no teste. Ele mede
quando a carga aconteceu, não o que ela trouxe. Sem orquestrador, ninguém roda o
comando sozinho; aqui ele roda no CI logo depois da ingestão.

---

## 2. Metadados de execução

**O que fica gravado.** Hooks do dbt, em `dbt/macros/metadados.sql`, sem pacote
externo:

| Tabela | Grão | Para que serve |
|---|---|---|
| `meta.execucoes_dbt` | uma linha por comando (`build`, `test`, `run`, `freshness`...) | quando rodou, quanto durou e quantos nós passaram, avisaram ou falharam |
| `meta.resultados_dbt` | uma linha por model ou teste de cada comando | qual teste falhou, quantas linhas, quanto tempo, mensagem |
| `marts.atualizacao_dados` | uma linha, reescrita a cada `dbt build` completo | o rodapé do dashboard |

Exemplo real, do build completo no dataset inteiro:

| comando | nós | sucesso | aviso | erro | duração |
|---|---|---|---|---|---|
| build | 106 | 103 | 3 | 0 | 1 min 11 s |

E o texto que vai para o rodapé:

> Dados processados em 08/10/2026 16:39 (Brasília) · 81 testes ok, 3 avisos

Os 106 nós são 22 models e 84 testes. O resumo do próprio dbt mostra PASS=106
porque conta também os 3 hooks.

**Por que `atualizacao_dados` mora em `marts`.** O publicador do Neon copia o
schema `marts` inteiro e descobre tabelas novas sozinho. Assim a linha chega ao
Looker sem mudar o script. O histórico (`meta.*`) fica só no Postgres local.

**Por que só o `build` completo reescreve o rodapé.** O rodapé diz quando o
projeto inteiro foi processado. Um `dbt test` sozinho não processa nada, e um
build parcial (`--select`, como o `make reprocessar`) contaria só parte dos
testes: os dois entram no histórico, mas não mudam a linha do rodapé. Num build
completo com falha, o texto mostra os erros de qualquer model ou teste, e os nós
pulados. O `validate_incremental.py` confere o `dbt test` e o build com janela.

**Duas armadilhas pagas na montagem:**

- **Hook renderizado sem grafo.** No parse completo, o dbt renderiza o
  `on-run-end` antes de carregar o grafo, e a macro quebrava ao ler
  `graph.sources`. A guarda `if not execute` resolve. A validação agora força
  um build com `--no-partial-parse` para não deixar isso voltar.
- **Aspas em mensagem de erro.** A mensagem do dbt entra num `insert`; uma
  aspa simples nela quebraria o próprio hook. A macro `texto_sql` dobra as
  aspas e trunca em 500 caracteres, e o `dbt run-operation testa_texto_sql`
  testa isso.

**O que pode dar errado em produção.** Se o próprio `on-run-end` falhar, o dbt
reporta erro mesmo com os models construídos. É melhor que um metadado faltando
em silêncio, mas o alerta é sobre o registro, não sobre o dado. O histórico cresce
sem limite: em produção, uma política de retenção (por exemplo, 90 dias) entraria
junto.

---

## 3. Reprocessamento por janela

```sh
dbt build --profiles-dir . --select fato_pedidos fato_itens_pedido \
  --vars '{janela_inicio: 2018-03-01, janela_fim: 2018-04-01}'
# ou: make reprocessar INICIO=2018-03-01 FIM=2018-04-01
```

**O pedido.** Refazer só um período, por exemplo depois de corrigir os dados de
março na origem, sem comparar o fato inteiro, e refletir inclusive exclusões.

**Como funciona.** Com as duas vars, num build incremental:

1. um `pre_hook` apaga do fato as linhas com compra dentro da janela;
2. o model seleciona só os pedidos da janela, sem o `EXCEPT`;
3. o `delete+insert` grava essas linhas.

O hook roda na mesma transação do model: em cada fato, a janela é trocada
inteira ou não é trocada. Os dois fatos rodam em transações separadas; se um
falhar e o outro não, eles ficam fora de sincronia naquela janela até a próxima
execução, que deve ser repetida. A janela é pela data da compra, que não muda depois do pedido, então
nenhum registro migra de uma janela para outra. Sem as vars, os fatos seguem a
comparação completa de antes.

**O que a validação prova.** No banco descartável:

- um pedido de março apagado na origem some dos dois fatos;
- um pedido de 2017 alterado na origem **não** muda, porque está fora da janela;
- as outras linhas de março ficam com o mesmo conteúdo;
- um build normal depois aplica a alteração de 2017;
- o resultado final é igual ao de um `--full-refresh`, em todas as colunas.

**Proteções.** As vars são validadas antes de qualquer `delete`:

| Entrada | Resultado |
|---|---|
| só `janela_inicio` | erro de compilação: "Janela incompleta: falta janela_fim" |
| início depois do fim | erro: "Janela vazia ou invertida" |
| data impossível (`2018-02-30`) | erro: "day is out of range for month" |
| janela com `--full-refresh` ou tabela nova | vars ignoradas, com aviso no log; o fato é reconstruído inteiro |

**Por que não `incremental_predicates`.** Ele restringe o `delete` às chaves que
vieram no delta. Uma chave que sumiu da origem não vem no delta, então nunca seria
apagada. Substituir a partição inteira é o que reflete a exclusão.

**O que pode dar errado em produção.** A janela confia na data da compra como
chave de partição. Se um dia a regra mudar (por exemplo, janela pela data de
entrega), um registro pode mudar de partição e ficar duplicado ou perdido. A
validação pega isso só para o que ela testa. E reprocessar uma janela não
reconstrói as dimensões nem as OBTs: depois de corrigir um período, rode o build
normal para as tabelas derivadas.

---

## 4. CI enxuto

**Antes.** O workflow rodava em `push` para qualquer branch e em `pull_request`:
cada PR rodava duas vezes, e todo push reconstruía o projeto inteiro.

**Agora:**

| Evento | O que roda |
|---|---|
| `pull_request` | pytest, ingestão, freshness; `dbt build --select +state:modified+` contra o manifest da branch base; validação incremental só se os fatos estiverem na seleção |
| `push` na `main` | pytest, ingestão, freshness, `dbt build` completo e validação incremental |

O manifest da base vem de um `git worktree` da branch base com `dbt parse`, que
não precisa de banco. Um PR que só mexe em documentação, no dashboard ou no Python
do modelo seleciona zero models e não reconstrói nada.

**Por que `+state:modified+` e não `--defer`.** O padrão em produção é
`state:modified+ --defer`: constrói só o que mudou e lê o resto do ambiente de
produção. Aqui o banco do CI começa vazio a cada execução e não existe produção
para onde adiar, então os ancestrais do que mudou também entram (o `+` da
esquerda). Com este projeto pequeno, o ganho real é o caso de seleção vazia.

**O que pode dar errado.** Uma mudança que quebra algo fora da seleção, como um
hook do projeto ou uma tabela criada por hook, só aparece no build completo da
`main`, depois do merge. Por isso a `main` continua com tudo. E mudança só no
`dbt_project.yml` que afete todos os models (como um `post-hook` de pasta)
seleciona o projeto inteiro: o CI enxuto vira o completo, corretamente.

---

## 5. Um achado do caminho: estatísticas

Depois de recarregar a raw, o `dbt build` travou por mais de 5 minutos no
`ml_features_atraso`, um model que levava segundos. O plano de execução estimava
**418 bilhões de linhas**. Duas causas:

- o dbt cria uma tabela e o model seguinte a consulta antes de o autovacuum
  calcular as estatísticas dela;
- um CTE usado duas vezes (`geo`) era materializado, e CTE materializado não tem
  estatística: o planner supunha CEP repetido e multiplicava as linhas.

Correção: `analyze` como `post-hook` das tabelas de `marts` e `ml`, e o CTE como
`not materialized`. Medido isolado, o model caiu de 74 para 13 segundos (a
consulta sozinha, de 74 para 8); num build completo, em paralelo com outros
models, ele leva de 20 a 45 segundos. O conteúdo é o mesmo
(md5 da tabela idêntico antes e depois). Em produção, isso aparece como "o job
que às vezes demora 10 vezes mais", porque depende de o autovacuum chegar antes ou
depois.

