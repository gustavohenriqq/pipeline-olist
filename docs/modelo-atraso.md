# Previsão de atraso no ato da compra

Etapa 4 do projeto. Modelo que estima, no momento em que o pedido é feito, a
probabilidade de ele chegar depois da data prometida, e grava essa estimativa em
`marts.previsao_atraso`. Todos os números deste documento saem de
[`ml/artefatos/metricas.json`](../ml/artefatos/metricas.json) (versão
`20261008-0b8827c0`) e da primeira execução, guardada em
[`metricas_execucao1_com_mes_compra.json`](../ml/artefatos/metricas_execucao1_com_mes_compra.json).
A seção 12 (histórico do vendedor) usa
[`metricas_execucao3_com_historico_vendedor.json`](../ml/artefatos/metricas_execucao3_com_historico_vendedor.json)
e [`ablacao_historico_vendedor_validacao.json`](../ml/artefatos/ablacao_historico_vendedor_validacao.json).
A especificação está em [docs/specs](specs/2026-10-08-previsao-atraso-design.md).

---

## Resumo

**O modelo ordena risco melhor que a régua simples.** No teste (mai a ago/2018),
o gradient boosting tem PR-AUC de **0,085** contra **0,049** da baseline por UF,
numa base com 4,4% de atraso. Os 10% de pedidos que ele considera mais
arriscados atrasam **10,0%** das vezes; os 10% menos arriscados, **1,0%**.

**Mas o alerta não se paga no período de teste.** Com a hipótese declarada (ação
preventiva R$ 15, atraso não evitado R$ 60), alertar só compensa se mais de 25%
dos pedidos marcados forem atrasar. O limiar escolhido na validação (0,11) acerta
**9,4%** no teste. Resultado: R$ 99.510 de custo contra R$ 66.900 de não fazer
nada. Na validação o custo fica abaixo de "nunca agir", mas isso não prova
nada: o limiar foi escolhido justamente para minimizar o custo ali.

**A leitura mais provável:** o valor do alerta depende do regime de atraso, mais
do que da qualidade do modelo. O limiar foi escolhido num período com 10,8% de
atraso e aplicado num período com 4,4%; com menos atrasos, a precisão cai abaixo
do ponto de equilíbrio. Os meses de crise (fev e mar/2018) são consistentes com
essa leitura, mas estão dentro do período em que o limiar foi escolhido, então
não a provam sozinhos.

**A validação expôs um erro de desenho meu.** A primeira execução usava o mês da
compra como feature, e o modelo principal perdia para a regressão logística e
até para a baseline na validação. O PSI de 4,92 dessa coluna entre treino e
teste confirma o descompasso (seria alto para qualquer feature de calendário,
já que o teste cobre só 4 meses do ano). Com um só ano de treino, o mês do ano decora o que
aconteceu em cada mês de 2017; não ensina sazonalidade. A coluna saiu, e a seção
"Primeira execução" conta o que mudou, inclusive que o teste foi olhado duas
vezes.

**O histórico do vendedor não ajudou, e ficou fora do modelo.** A taxa de
atraso de cada vendedor, calculada só com pedidos entregues antes do dia da
compra, era a feature com mais chance de melhorar o modelo. Ela não vaza (um
teste dbt recalcula tudo e falha se entrar pedido posterior), mas derrubou a
PR-AUC da validação de 0,235 para 0,213, e nenhuma das cinco variantes
testadas ficou acima da versão sem histórico. Sozinha, ela quase não ordena o
risco (ROC-AUC 0,526 na validação). Detalhes na seção 12.

---

## 1. A pergunta e o uso

Prever, no ato da compra, se o pedido vai atrasar, para disparar uma ação
preventiva (avisar o cliente, folgar o prazo ou priorizar o frete). A Etapa 2
mostrou o tamanho do problema: uma semana de atraso derruba a nota de 4,29 para
2,72.

O que precisava ficar visível era rigor: auditoria de vazamento, separação
temporal, baseline antes do modelo e limiar escolhido por custo. Uma métrica alta
conseguida com vazamento vale menos que uma métrica modesta e honesta.

## 2. Auditoria de features

As features são montadas em SQL, no model dbt `ml.ml_features_atraso`, e o Python
só aceita as colunas da lista `PERMITIDAS` em `ml/features.py`: `matriz()`
descarta qualquer outra coluna, e um teste impede que um campo da lista
`PROIBIDAS` entre na permitida. A lista proibida é mantida à mão; um campo
posterior à compra com nome novo precisa ser auditado por quem o adicionar.

**Permitidas** (todas existem no ato da compra): prazo prometido em dias, UF e
região do cliente e do vendedor principal, venda entre regiões, distância entre
os CEPs, valor dos itens e do frete, frete sobre valor, quantidade de itens, de
vendedores e de produtos, peso e volume, grupo de categoria do item de maior
valor, forma de pagamento de maior valor, parcelas, dia da semana e hora da
compra.

**Calculadas, mas fora por desempenho:** `vendedor_entregas_hist` e
`vendedor_taxa_atraso_hist` (histórico do vendedor na data da compra). Não
vazam, mas pioraram a validação; ficam na lista `FORA_POR_DESEMPENHO` de
`ml/features.py`, e `matriz()` as descarta (seção 12).

**Proibidas, e por quê:**

| Campo | Motivo |
|---|---|
| `approved_at` | acontece depois da compra (boleto pode levar dias) |
| `delivered_carrier_at`, `dias_ate_transportadora` | acontece depois da compra |
| `delivered_customer_at`, `tempo_entrega_dias`, `dias_em_transporte` | é o próprio desfecho |
| `atraso_dias`, `entregue_no_prazo` | é o alvo |
| `nota_avaliacao` | avaliação é posterior à entrega |
| `order_status`, `status_pedido`, `situacao_pedido` | o status muda ao longo da vida do pedido |
| `valor_pago`, `qtd_pagamentos` | redundantes com valor e parcelas |
| `ano_compra` | o ano não se repete no futuro |
| `mes_compra` | com um só ano de treino, decora 2017 (ver "Primeira execução") |

**O que o vazamento produz.** O mesmo modelo, treinado uma vez a mais com
`atraso_dias` incluído de propósito, chega a **ROC-AUC 1,000 e PR-AUC 1,000** na
validação. É o número que um modelo com vazamento mostraria, e não serve para
nada: no momento da compra esse campo não existe. Esse modelo não é salvo.

**Dois problemas de dado encontrados no caminho:**

- **Distância de 20 mil km.** No Postgres, `least(1, null)` devolve 1, e não
  nulo. O haversine usava `least` para proteger o arco-seno, e 493 pedidos com
  CEP sem coordenada ganharam a distância máxima da Terra. Um teste dbt
  (`assert_distancia_km_plausivel`, nada acima de 4.500 km) pegou o bug, e o
  cálculo passou a usar `case`.
- **CEP do Paraná na Espanha.** Onze prefixos de CEP da base de geolocalização
  têm coordenada média fora do Brasil. Nas features, ponto fora da caixa do país
  é descartado e a distância fica nula; a dimensão do dashboard não muda.

No fim, 502 dos 97.910 pedidos ficam com distância nula. O modelo principal
trata nulo nativamente; a logística imputa a mediana.

## 3. Separação temporal

| Conjunto | Compras | Pedidos | Taxa de atraso |
|---|---|---|---|
| Treino | jan a dez/2017 | 43.426 | 5,6% (contagem direta em `ml.ml_features_atraso`) |
| Validação | jan a abr/2018 | 27.425 | 10,8% |
| Teste | mai a ago/2018 | 25.352 | 4,4% |
| Em andamento | toda a janela, sem entrega | 1.707 | sem resposta |

**Por que no tempo e não aleatório.** Em produção o modelo sempre prevê o futuro
com o passado. Um split aleatório deixaria pedidos de março de 2018 no treino e
no teste ao mesmo tempo, e o modelo "veria" a crise de março antes de ela
acontecer.

A taxa de atraso muda muito de um período para o outro: 10,8% na validação e
4,4% no teste. Essa diferença explica quase tudo o que vem a seguir.

## 4. Resultados

Três modelos, cada um com o limiar escolhido por custo na validação:

1. **Baseline:** taxa de atraso do treino por UF do cliente.
2. **Regressão logística:** numéricas padronizadas, categóricas em one-hot.
3. **Modelo principal:** `HistGradientBoostingClassifier`, com hiperparâmetros
   escolhidos numa grade de 12 combinações pela PR-AUC da validação (todas ficaram
   entre 0,226 e 0,235; a escolhida foi taxa 0,1, profundidade 3, 20 amostras
   por folha).

**Validação** (jan a abr/2018, taxa 10,8%, "nunca agir" custa R$ 177.780):

| Modelo | PR-AUC | ROC-AUC | Limiar | Precisão | Recall | Alertas/mil | Custo (R$) |
|---|---|---|---|---|---|---|---|
| Baseline | 0,179 | 0,648 | 0,14 | 28,5% | 3,8% | 14,5 | 176.955 |
| Logística | 0,244 | 0,705 | 0,11 | 32,9% | 27,8% | 91,3 | 165.885 |
| Principal | 0,235 | 0,705 | 0,11 | 30,6% | 29,8% | 105,2 | 168.135 |

**Teste** (mai a ago/2018, taxa 4,4%, "nunca agir" custa R$ 66.900, "agir
sempre" R$ 380.280):

| Modelo | PR-AUC | ROC-AUC | Brier | Precisão | Recall | Alertas/mil | Custo (R$) |
|---|---|---|---|---|---|---|---|
| Baseline | 0,049 | 0,529 | 0,0427 | 8,3% | 2,3% | 12,4 | 70.065 |
| Logística | 0,083 | 0,689 | 0,0420 | 8,9% | 22,4% | 111,3 | 94.230 |
| Principal | 0,085 | 0,680 | 0,0421 | 9,4% | 29,4% | 137,5 | 99.510 |

**Como ler.** PR-AUC é a métrica principal porque a classe positiva é rara; o
valor de referência de um modelo sem informação é a própria taxa de atraso (0,044
no teste). O principal fica em quase duas vezes isso; a baseline por UF, quase
no acaso. A logística empata com o gradient boosting: o sinal disponível no ato
da compra é modesto, e um modelo mais flexível não acha muito mais que um
linear.

**Critérios da especificação:**

1. Nenhuma feature posterior à compra, verificado por teste: **cumprido.**
2. Principal supera a baseline em PR-AUC no teste: **cumprido** (0,085 contra 0,049).
3. Limiar com custo menor que "nunca agir" e "agir sempre": **não cumprido.**
   Só faz sentido medir fora da amostra (na validação o custo é menor por
   construção), e no teste o alerta custa mais que não agir. Próxima seção.
4. Tabela no Postgres local e no Neon, com testes dbt passando: **cumprido.**
   97.910 linhas nos dois; testes da source passando no local, e as mesmas
   verificações (chave única e não nula, relacionamento com o fato,
   probabilidade entre 0 e 1, valores de `conjunto`) conferidas no Neon em
   08/10/2026.
5. Este documento: **cumprido.**

## 5. Limiar e custo

> **Hipótese inventada e declarada:** ação preventiva custa R$ 15 por pedido
> marcado; atraso não evitado custa R$ 60. A ação é tratada como eficaz quando
> aplicada a um pedido que de fato atrasaria. Nenhum desses números vem de dado
> real.

Com essa hipótese, um alerta só se paga se a chance de atraso do pedido marcado
passar de 15/60 = **25%**. Na validação, onde o limiar foi escolhido, a precisão
ficou em 30,6%. No teste, com a taxa de atraso em menos da metade, caiu para
9,4%, e cada alerta passou a custar mais do que evitava.

**Sensibilidade** (ação fixa em R$ 15, limiar escolhido na validação para cada
razão, custo medido no teste):

| Razão | Custo do atraso | Limiar | Alertas/mil | Custo no teste | Nunca agir | Agir sempre |
|---|---|---|---|---|---|---|
| 1:2 | R$ 30 | 0,40 | 0,0 | 33.450 | 33.450 | 380.280 |
| 1:4 | R$ 60 | 0,11 | 137,5 | 99.510 | 66.900 | 380.280 |
| 1:8 | R$ 120 | 0,06 | 375,3 | 193.470 | 133.800 | 380.280 |

Em nenhuma razão o alerta bate "nunca agir" no teste. Na razão 1:2 o limiar
escolhido já não marca nenhum pedido. A decisão muda muito com a razão, e o
documento não esconde isso: o número que mais importa para decidir se vale agir
é a taxa de atraso do momento, não a hipótese de custo.

**O que eu faria em produção** (fora do escopo desta etapa):

- reescolher o limiar com uma janela recente, em vez de fixá-lo uma vez;
- ou trocar o limiar por capacidade: alertar os N pedidos mais arriscados por
  dia, o número que a operação consegue tratar. A ordenação do modelo se
  sustenta mesmo quando a taxa muda (ver calibração e backtest).

## 6. Calibração

Por decil de probabilidade no teste:

| Decil | Probabilidade média | Atraso real | Pedidos |
|---|---|---|---|
| 1 | 1,9% | 1,0% | 2.536 |
| 2 | 2,7% | 1,5% | 2.535 |
| 3 | 3,2% | 2,2% | 2.535 |
| 4 | 3,8% | 2,7% | 2.535 |
| 5 | 4,4% | 3,4% | 2.535 |
| 6 | 5,2% | 4,7% | 2.535 |
| 7 | 6,3% | 5,3% | 2.535 |
| 8 | 8,0% | 6,1% | 2.535 |
| 9 | 10,7% | 7,2% | 2.535 |
| 10 | 16,9% | 10,0% | 2.536 |

A ordem está certa (o atraso real sobe de decil em decil), mas a probabilidade
está sistematicamente alta: o modelo superestima o risco num período mais calmo
que o treino. É o mesmo problema do limiar visto por outro ângulo.

## 7. Backtest mensal

Para cada mês de 2018, o modelo principal (mesmos hiperparâmetros) é treinado com
todos os pedidos anteriores ao mês e avaliado no mês. Custos com o limiar 0,11.
Atenção: limiar e hiperparâmetros foram escolhidos com jan a abr/2018, então
esses quatro meses (marcados com *) não são fora da amostra para o custo.

| Mês | Pedidos | Taxa | PR-AUC 1ª execução | PR-AUC atual | PR-AUC / taxa | Custo (R$) | Nunca agir (R$) |
|---|---|---|---|---|---|---|---|
| 2018-01* | 7.069 | 5,7% | 0,102 | 0,125 | 2,2x | 27.615 | 24.180 |
| 2018-02* | 6.555 | 14,1% | 0,262 | 0,292 | 2,1x | 50.355 | 55.560 |
| 2018-03* | 7.003 | 19,0% | 0,308 | 0,372 | 2,0x | 67.740 | 79.680 |
| 2018-04* | 6.798 | 4,5% | 0,125 | 0,176 | 3,9x | 31.410 | 18.360 |
| 2018-05 | 6.749 | 6,6% | 0,137 | 0,166 | 2,5x | 36.390 | 26.580 |
| 2018-06 | 6.096 | 1,2% | 0,055 | 0,103 | 8,9x | 13.335 | 4.260 |
| 2018-07 | 6.156 | 3,4% | 0,075 | 0,092 | 2,7x | 36.930 | 12.480 |
| 2018-08 | 6.351 | 6,2% | 0,123 | 0,071 | 1,1x | 42.255 | 23.580 |

Três leituras:

- **A ordenação é estável:** de janeiro a julho, a PR-AUC fica entre 2 e 9 vezes a
  taxa base.
- **O custo só fica abaixo de "nunca agir" em fevereiro e março**, os dois meses
  com taxa acima de 14%. É consistente com o ponto de equilíbrio de 25%, mas
  ambos estão dentro do período de escolha do limiar. Nos quatro meses fora da
  amostra (mai a ago), o alerta não se paga em nenhum.
- **Agosto é o ponto fraco:** a PR-AUC cai para quase o acaso (1,1x). É o mês em
  que o prazo médio prometido despencou para 15,8 dias (20,3 em julho, contra 23 a 28 antes), e
  o drift abaixo mostra essa mudança.

## 8. Drift

PSI (índice de estabilidade populacional) de cada feature, em 10 faixas pelos
quantis do treino. Acima de 0,2 é sinalizado.

**Treino contra teste**, as que passaram de 0,05:

| Feature | PSI | Sinalizado |
|---|---|---|
| `prazo_prometido_dias` | 0,391 | sim |
| `valor_frete` | 0,288 | sim |
| `categoria_grupo` | 0,098 | não |
| `vendedor_uf` | 0,085 | não |

O prazo prometido mudou como a especificação esperava: a plataforma passou a
prometer prazos mais curtos no fim da série. O modelo foi treinado num mundo em
que prazo curto era raro e arriscado.

**Treino contra em andamento:** nenhuma feature passou de 0,2 (a maior,
`cliente_uf`, ficou em 0,091). Os 1.707 pedidos sem entrega estão espalhados por
toda a janela, não concentrados no fim, então essa comparação mede pouco. Em
produção, a comparação útil é treino contra os pedidos das últimas semanas.

## 9. Primeira execução: o erro do mês da compra

A primeira execução treinou com `mes_compra` entre as features. A especificação
tinha excluído `ano_compra` porque o ano não se repete; o mesmo argumento vale
para o mês quando o treino tem um só ano. O modelo não aprende "novembro tem
Black Friday"; aprende "novembro de 2017 atrasou 12,4%", e "fevereiro e março
foram calmos", justamente os meses da crise de 2018 (14,1% e 19,0%).

O que denunciou o problema:

| | 1ª execução (com mês) | Atual (sem mês) |
|---|---|---|
| PSI de `mes_compra`, treino contra teste | 4,92 | (fora do modelo) |
| Principal, PR-AUC na validação | 0,173 | 0,235 |
| Principal, ROC-AUC na validação | 0,619 | 0,705 |
| Logística, PR-AUC na validação | 0,236 | 0,244 |
| Principal, PR-AUC no teste | 0,087 | 0,085 |
| Principal, ROC-AUC no teste | 0,698 | 0,680 |
| Principal, limiar e custo no teste (R$) | 0,16 e 71.265 | 0,11 e 99.510 |

Na validação, o gradient boosting com o mês ficava abaixo da logística e até da
baseline (0,179). Sem o mês, ele empata com a logística, e o backtest melhora em
sete dos oito meses.

**Transparência sobre o teste.** A especificação manda usar o teste uma vez só.
Ele foi usado duas: a remoção do mês foi decidida depois de ver a primeira
execução inteira, teste incluído. A decisão se sustenta só com a validação e com
o argumento do `ano_compra`, mas quem lê os números do teste deve saber disso. A
execução atual é um pouco pior no teste em todas as medidas (PR-AUC 0,087 para
0,085, ROC-AUC 0,698 para 0,680, custo R$ 71.265 para R$ 99.510), o que indica
que a mudança não foi feita para melhorar o teste.

## 10. A tabela `marts.previsao_atraso`

Uma linha por pedido da janela (97.910), escrita por `ml/inferir.py` com o modelo
final: o principal retreinado com treino e validação, e o limiar 0,11.

| Coluna | Descrição |
|---|---|
| `pedido_sk` | chave do `fato_pedidos` |
| `prob_atraso` | probabilidade entre 0 e 1 |
| `alerta` | `prob_atraso` maior ou igual ao limiar |
| `conjunto` | `treino`, `validacao`, `teste` ou `em_andamento` |
| `limiar`, `modelo_versao`, `gerado_em` | rastreio de qual modelo gerou a linha |

**Cuidado ao ler no dashboard:**

- Previsões sobre `treino` e `validacao` são otimistas: o modelo final viu esses
  pedidos. Só `teste` e `em_andamento` são honestas.
- O modelo final aprendeu com fev e mar/2018, de atraso alto, e por isso alerta
  mais que o modelo avaliado: na inferência, 313 de cada mil pedidos do teste
  ficaram em alerta, contra 137,5 por mil do modelo avaliado acima. Entre os
  pedidos em andamento, 531 de 1.707. É mais um motivo para tratar o alerta como
  ordenação de risco, não como decisão automática.

A tabela é criada vazia pelo dbt (hook `on-run-start`) e testada como source:
chave única e não nula, relacionamento com `fato_pedidos`, probabilidade entre 0
e 1 e valores aceitos de `conjunto`. Rodar a inferência duas vezes grava o mesmo
número de linhas.

## 11. Limites e próximos passos

- **Histórico do vendedor em janela recente.** A taxa acumulada foi testada e
  piorou o modelo (seção 12). Ainda não testados: a taxa só dos últimos 90 dias,
  que esquece crises antigas, e o tempo histórico de despacho do vendedor (dias
  até a transportadora), que é a parte do atraso que ele controla.
- **Limiar adaptativo ou por capacidade** (seção 5).
- **Mais de um ano de dados** antes de qualquer feature de calendário anual.
- **Recalibrar as probabilidades** numa janela recente.
- **Página no Looker** com os pedidos em andamento ordenados por risco.
- **Retreino agendado e alerta de drift.** Aqui o PSI é uma medição pontual,
  registrada neste documento, não monitoramento.
- **Censura:** pedidos sem entrega ficam fora do treino. São cerca de 2% por mês,
  então o viés é pequeno, mas existe.

## 12. Histórico do vendedor (issue 18)

A pergunta: saber como o vendedor vinha entregando melhora a previsão? É a
feature que mais parecia faltar, e a mais fácil de vazar: a taxa de atraso do
vendedor calculada com a base inteira inclui os atrasos que ainda iam acontecer.

**Como é calculada.** O model `ml.ml_historico_vendedor` guarda, para cada par
(pedido, vendedor), quantos pedidos daquele vendedor tinham sido **comprados e
entregues antes do dia da compra**, quantos desses atrasaram e a mesma conta para
a plataforma inteira. Entrega no próprio dia da compra fica de fora, porque o
modelo roda no ato da compra e não sabe a hora da entrega. Pedido em trânsito
não conta, mesmo vencido: só pedido entregue tem desfecho fechado. Em
`ml_features_atraso` entram duas colunas, do vendedor principal:

- `vendedor_entregas_hist`: o número de entregas anteriores (0 para vendedor
  novo; 5,4% dos pedidos da janela);
- `vendedor_taxa_atraso_hist`: (atrasos + 10 × taxa geral do dia) / (entregas +
  10). Vendedor sem histórico recebe a taxa geral daquela data; com 10 entregas,
  pesa meio a meio. O peso 10 foi fixado antes de treinar, sem busca.

**O teste contra o futuro.** `assert_historico_vendedor_sem_futuro` recalcula as
contagens por junção direta, com a regra escrita por extenso (entrega anterior
ao dia da compra e compra anterior ao dia da compra), sem a soma acumulada que o
model usa, e falha se algum número divergir ou se a última entrega usada não for
anterior ao dia da compra. Prova de que ele pega o erro: com a ordem dos eventos
invertida no model, de modo que a entrega do próprio dia passasse a contar, o
teste devolveu 77.214 linhas com problema (38.607 pares). O model também se
protege de pedido entregue antes da própria compra, mas a base não tem nenhum,
então essa proteção não muda nada hoje.

**Resultado no mesmo split** (treino 2017, validação jan a abr/2018, teste mai a
ago/2018), a execução completa de `ml.treinar` com as duas colunas, contra a
versão atual:

| Conjunto | Modelo | PR-AUC atual | PR-AUC com histórico | ROC-AUC atual | ROC-AUC com histórico | Brier atual | Brier com histórico |
|---|---|---|---|---|---|---|---|
| Validação | Baseline | 0,179 | 0,179 | 0,648 | 0,648 | 0,0965 | 0,0965 |
| Validação | Logística | 0,244 | 0,218 | 0,705 | 0,687 | 0,0945 | 0,0928 |
| Validação | Principal | 0,235 | 0,213 | 0,705 | 0,688 | 0,0943 | 0,0936 |
| Teste | Baseline | 0,049 | 0,049 | 0,529 | 0,529 | 0,0427 | 0,0427 |
| Teste | Logística | 0,083 | 0,073 | 0,689 | 0,659 | 0,0420 | 0,0469 |
| Teste | Principal | 0,085 | 0,076 | 0,680 | 0,657 | 0,0421 | 0,0482 |

A baseline idêntica confirma que as duas execuções viram os mesmos pedidos. Com
o histórico, a grade escolheu outra combinação (profundidade livre em vez de 3)
e o limiar subiu de 0,11 para 0,21. O custo no teste caiu de R$ 99.510 para
R$ 86.985, mas só porque o modelo passou a alertar menos (83 por mil em vez de
137,5); continua acima dos R$ 66.900 de não fazer nada, e a precisão caiu (9,4%
para 9,2%). No backtest mensal, a PR-AUC piorou em 6 dos 8 meses de 2018.

**Calibração no teste**, por decil (probabilidade média / atraso real):

| Decil | Atual | Com histórico |
|---|---|---|
| 1 | 1,9% / 1,0% | 1,8% / 1,4% |
| 2 | 2,7% / 1,5% | 2,7% / 1,9% |
| 3 | 3,2% / 2,2% | 3,4% / 2,6% |
| 4 | 3,8% / 2,7% | 4,1% / 2,8% |
| 5 | 4,4% / 3,4% | 5,0% / 3,6% |
| 6 | 5,2% / 4,7% | 6,3% / 4,3% |
| 7 | 6,3% / 5,3% | 8,1% / 4,9% |
| 8 | 8,0% / 6,1% | 10,7% / 6,7% |
| 9 | 10,7% / 7,2% | 15,3% / 7,2% |
| 10 | 16,9% / 10,0% | 30,4% / 8,6% |

A calibração piora onde importa: os 10% mais arriscados recebem 30,4% de
probabilidade e atrasam 8,6%, menos que os 10,0% do modelo atual. O topo da
lista ficou pior, não melhor.

**Ablação, só na validação** (hiperparâmetros do modelo atual fixos, para
isolar o efeito das colunas; o teste não foi calculado). PR-AUC:

| Variante | Principal | Logística |
|---|---|---|
| Sem histórico (atual) | 0,236 | 0,244 |
| Só a contagem | 0,229 | 0,230 |
| Só a taxa | 0,217 | 0,226 |
| Contagem e taxa | 0,205 | 0,218 |
| Contagem e taxa relativa à taxa geral | 0,228 | 0,231 |

Nenhuma variante passa a versão sem histórico. (A linha "sem histórico" dá 0,236
contra os 0,235 registrados: o banco usado aqui devolve os pedidos em outra
ordem, e a parada antecipada do gradient boosting sorteia outra fatia interna.
A logística, sem sorteio, repete 0,244.)

**Por que não funcionou.** Três leituras, da mais para a menos sustentada:

1. **O sinal é fraco.** Sozinha, a taxa do vendedor tem ROC-AUC de 0,557 no
   treino e 0,526 na validação, quase o acaso. É coerente com a Etapa 2: só 13%
   do atraso nasce no vendedor, o resto é transporte ([análise](analise-atraso.md)).
2. **A taxa acumulada carrega o regime.** O PSI da taxa entre treino e teste é
   2,82, o maior de todas as features. Em 2017 o histórico era curto e calmo; no
   teste, todo vendedor carrega os atrasos da crise de fev e mar/2018 num período
   com 4,4% de atraso. O modelo lê isso como risco, e é daí que vem o topo
   superestimado da calibração. A taxa relativa à taxa geral do dia corrige o
   nível e recupera parte da perda, mas não passa a versão sem histórico.
3. **Censura.** Pedido atrasado demora mais para entrar no histórico, porque só
   conta depois de entregue. A taxa média da feature é 2,5% no treino, contra
   5,6% de atraso real. Isso não é vazamento (é o que existiria em produção
   naquele dia), mas achata a diferença entre vendedores.

**Decisão.** As colunas continuam calculadas e testadas no dbt, prontas para
uma versão melhor (janela recente, tempo de despacho), mas ficam fora da lista
permitida. O modelo salvo, `metricas.json` e `marts.previsao_atraso` não mudam,
e por isso nada muda no Power BI nem no painel. Se um dia as colunas entrarem,
a previsão muda inteira: a página de risco, a contagem de alertas, a receita em
risco e o caso de conferência `html_risco_linhas` (que espera o pedido do topo
com 52,5%) precisam ser refeitos.

**Transparência sobre o teste.** A execução completa calcula o teste junto, e
ele foi olhado pela terceira vez. A decisão de deixar as colunas de fora se
sustenta só com a validação (as duas famílias de modelo pioram lá), e a ablação
foi feita depois, sem tocar no teste.

## Como reproduzir

```bash
cd dbt && dbt build --profiles-dir . && cd ..
python -m ml.treinar      # grava ml/artefatos/modelo.joblib e metricas.json
python -m ml.inferir      # grava marts.previsao_atraso
cd dbt && dbt test --profiles-dir . --select source:ml_saida
python -m ml.ablacao_historico_vendedor   # seção 12, só validação
```

Para repetir a execução com o histórico do vendedor, mova as duas colunas de
`FORA_POR_DESEMPENHO` para `NUMERICAS` em `ml/features.py` e rode o treino.

Dependências em `requirements-ml.txt`. O CI roda os testes Python (`pytest
tests`), mas não o treino: os 800 pedidos da amostra não dão métrica que
signifique algo.
