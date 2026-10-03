# Incrementalidade dos fatos

`fato_pedidos` e `fato_itens_pedido` usam `incremental`, com `delete+insert`
pelas chaves `pedido_sk` e `item_sk`. As dimensoes e OBTs continuam como tabelas;
staging e intermediate continuam como views.

## Como o delta e identificado

Os CSVs do Olist sao snapshots estaticos, sem um `updated_at` confiavel em todas
as tabelas. Filtrar pela maior data de compra perderia uma correcao, um pagamento,
uma avaliacao ou um item que chegou depois para um pedido antigo.

Por isso, cada fato calcula seu resultado atual e usa `EXCEPT` contra o destino.
Essa comparacao inclui todas as colunas e considera dois NULLs iguais. Apenas
linhas novas ou diferentes seguem para `delete+insert`: a linha anterior com a
mesma chave e substituida na transacao do dbt. Se nada mudou, nenhuma linha do
fato e reescrita. As chaves continuam sujeitas aos testes de unicidade e nao nulo.

A primeira execucao cria a tabela inteira. Uma tabela ja existente, com o mesmo
schema, passa a receber deltas sem precisar de uma migracao manual.

## Comandos

Depois da ingestao, o comando habitual serve para a carga inicial e os deltas:

```sh
cd dbt
dbt build --profiles-dir .
```

Para reconstruir tudo, inclusive refletir exclusoes da origem ou uma mudanca
de schema:

```sh
dbt build --profiles-dir . --full-refresh
```

`on_schema_change='fail'` impede uma evolucao de schema silenciosa. O modo normal
nao remove uma chave que desapareceu do snapshot; nesse caso, use full-refresh.

Na pratica, isso pesa em toda coluna nova nos fatos. Se os fatos ja fossem
incrementais, `dias_ate_transportadora`, `dias_em_transporte` e `situacao_pedido`
teriam passado por isso, e o mesmo vale para a Etapa 4 se a previsao de atraso
entrar no `fato_pedidos`.
Com `fail`, o build normal para com erro em vez de seguir com a coluna faltando,
e a correcao e rodar `--full-refresh` uma vez. Por isso a previsao deve ir para
uma tabela propria, ligada ao fato pela chave, e nao para uma coluna do fato:
assim o modelo pode ser reprocessado sem reconstruir o fato inteiro.

## Limites

O delta reduz as escritas nos fatos, mas ainda le e compara o resultado completo.
A ingestao Python continua substituindo a raw inteira. Dimensoes e OBTs tambem
continuam sendo reconstruidas. Esta mudanca nao torna a carga ponta a ponta
incremental nem promete ganho de tempo com a amostra pequena. Uma fonte viva
com CDC ou timestamps de alteracao permitiria reduzir tambem a leitura.

## Validacao automatica

```sh
python scripts/validate_incremental.py
```

O CI executa esse comando usando a amostra versionada. Ele cria um banco com
nome aleatorio, testa e o remove ao final; o usuario do Postgres precisa de
`CREATEDB`. Nao altera o banco configurado como alvo.

Os cenarios cobrem:

- Build inicial e repetido: todas as colunas, chaves e versoes fisicas das linhas
  dos fatos permanecem iguais, demonstrando ausencia de duplicacao e reescrita.
- Pedido novo com data antiga e seus filhos; item novo ligado a pedido antigo.
- Correcao de status, transicao para NULL, preco, pagamento e avaliacao antigos.
- Conservacao das linhas que nao mudaram e reexecucao do delta sem novas escritas.
- Igualdade de todas as colunas dos fatos entre resultado incremental e full-refresh.

Os testes de qualidade existentes rodam em cada build, incluindo os relacionamentos
configurados como aviso.
