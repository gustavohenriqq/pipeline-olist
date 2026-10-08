# Incrementalidade dos fatos

`fato_pedidos` e `fato_itens_pedido` usam `incremental`, com `delete+insert`
pelas chaves `pedido_sk` e `item_sk`. As dimensões e OBTs continuam como tabelas;
staging e intermediate continuam como views.

## Como o delta é identificado

Os CSVs do Olist são snapshots estáticos, sem um `updated_at` confiável em todas
as tabelas. Filtrar pela maior data de compra perderia uma correção, um pagamento,
uma avaliação ou um item que chegou depois para um pedido antigo.

Por isso, cada fato calcula seu resultado atual e usa `EXCEPT` contra o destino.
Essa comparação inclui todas as colunas e considera dois NULLs iguais. Apenas
linhas novas ou diferentes seguem para `delete+insert`: a linha anterior com a
mesma chave é substituída na transação do dbt. Se nada mudou, nenhuma linha do
fato é reescrita. As chaves continuam sujeitas aos testes de unicidade e não nulo.

A primeira execução cria a tabela inteira. Uma tabela já existente, com o mesmo
schema, passa a receber deltas sem precisar de uma migração manual.

## Comandos

Depois da ingestão, o comando habitual serve para a carga inicial e os deltas:

```sh
cd dbt
dbt build --profiles-dir .
```

Para reconstruir tudo, inclusive refletir exclusões da origem ou uma mudança
de schema:

```sh
dbt build --profiles-dir . --full-refresh
```

`on_schema_change='fail'` impede uma evolução de schema silenciosa. O modo normal
não remove uma chave que desapareceu do snapshot; nesse caso, use full-refresh ou
o reprocessamento por janela do período afetado.

Na prática, isso pesa em toda coluna nova nos fatos. Se os fatos já fossem
incrementais, `dias_ate_transportadora`, `dias_em_transporte` e `situacao_pedido`
teriam passado por isso, e o mesmo vale para a Etapa 4 se a previsão de atraso
entrar no `fato_pedidos`.
Com `fail`, o build normal para com erro em vez de seguir com a coluna faltando,
e a correção é rodar `--full-refresh` uma vez. Por isso a previsão deve ir para
uma tabela própria, ligada ao fato pela chave, e não para uma coluna do fato:
assim o modelo pode ser reprocessado sem reconstruir o fato inteiro.

## Reprocessar só uma janela

Para refazer um período sem comparar o fato inteiro, e refletindo inclusive
exclusões na origem, passe a janela pela data da compra (fim exclusivo):

```sh
dbt build --profiles-dir . --select fato_pedidos fato_itens_pedido \
  --vars '{janela_inicio: 2018-03-01, janela_fim: 2018-04-01}'
```

Um `pre_hook` apaga do fato as linhas da janela e o model insere as atuais, na
mesma transação. Fora da janela nada muda. Detalhes, proteções e o que a
validação prova estão em [confiabilidade.md](confiabilidade.md#3-reprocessamento-por-janela).

## Limites

O delta reduz as escritas nos fatos, mas ainda lê e compara o resultado completo.
A ingestão Python continua substituindo a raw inteira. Dimensões e OBTs também
continuam sendo reconstruídas. Esta mudança não torna a carga ponta a ponta
incremental nem promete ganho de tempo com a amostra pequena. Uma fonte viva
com CDC ou timestamps de alteração permitiria reduzir também a leitura.

## Validação automática

```sh
python scripts/validate_incremental.py
```

O CI executa esse comando usando a amostra versionada. Ele cria um banco com
nome aleatório, testa e o remove ao final; o usuário do Postgres precisa de
`CREATEDB`. Não altera o banco configurado como alvo.

Os cenários cobrem:

- Build inicial e repetido: todas as colunas, chaves e versões físicas das linhas
  dos fatos permanecem iguais, demonstrando ausência de duplicação e reescrita.
- Pedido novo com data antiga e seus filhos; item novo ligado a pedido antigo.
- Correção de status, transição para NULL, preço, pagamento e avaliação antigos.
- Conservação das linhas que não mudaram e reexecução do delta sem novas escritas.
- Igualdade de todas as colunas dos fatos entre resultado incremental e full-refresh.
- Reprocessamento por janela, freshness e metadados de execução (ver
  [confiabilidade.md](confiabilidade.md)).

Os testes de qualidade existentes rodam em cada build, incluindo os relacionamentos
configurados como aviso.
