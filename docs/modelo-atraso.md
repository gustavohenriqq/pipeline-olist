# Previsão de atraso no ato da compra

Etapa 4 do projeto. Modelo que estima, no momento em que o pedido é feito, a
probabilidade de ele chegar depois da data prometida, e grava essa estimativa em
`marts.previsao_atraso`. Todos os números deste documento saem de
[`ml/artefatos/metricas.json`](../ml/artefatos/metricas.json) (versão
`20261008-0b8827c0`) e da primeira execução, guardada em
[`metricas_execucao1_com_mes_compra.json`](../ml/artefatos/metricas_execucao1_com_mes_compra.json).
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
nada. Na validação (jan a abr/2018, 10,8% de atraso) o mesmo modelo economizava:
R$ 168.135 contra R$ 177.780.

**A leitura honesta:** o valor do alerta depende do regime de atraso, mais do que
da qualidade do modelo. Em meses de crise logística (fev e mar/2018, 14% e 19% de
atraso) a ação preventiva compensa; em meses calmos, não. Um limiar fixo,
escolhido num período, não serve para o outro.

**O monitor de drift pegou um erro de desenho meu.** A primeira execução usava o
mês da compra como feature. O PSI dessa coluna entre treino e teste deu **4,92**
(acima de 0,2 já é alerta), e o modelo principal perdia para a regressão
logística na validação. Com um só ano de treino, o mês do ano decora o que
aconteceu em cada mês de 2017; não ensina sazonalidade. A coluna saiu, e a seção
"Primeira execução" conta o que mudou, inclusive que o teste foi olhado duas
vezes.

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
só aceita as colunas da lista `PERMITIDAS` em `ml/features.py`. Um teste falha se
alguém puser na lista um campo proibido.

**Permitidas** (todas existem no ato da compra): prazo prometido em dias, UF e
região do cliente e do vendedor principal, venda entre regiões, distância entre
os CEPs, valor dos itens e do frete, frete sobre valor, quantidade de itens, de
vendedores e de produtos, peso e volume, grupo de categoria do item de maior
valor, forma de pagamento de maior valor, parcelas, dia da semana e hora da
compra.

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
| Treino | jan a dez/2017 | 43.426 | 5,7% (contagem direta em `ml.ml_features_atraso`) |
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
3. Limiar com custo menor que "nunca agir" e "agir sempre": **cumprido na
   validação, não no teste.** Explicação na próxima seção.

## 5. Limiar e custo

> **Hipótese inventada e declarada:** ação preventiva custa R$ 15 por pedido
> marcado; atraso não evitado custa R$ 60. A ação é tratada como eficaz quando
> aplicada a um pedido que de fato atrasaria. Nenhum desses números vem de dado
> real.

Com essa hipótese, um alerta só se paga se a chance de atraso do pedido marcado
passar de 15/60 = **25%**. Na validação, a precisão no limiar ficou em 30,6%, e o
modelo economizou R$ 9.645 (5,4%) contra não agir. No teste, com a taxa de
atraso em menos da metade, a precisão caiu para 9,4%, e cada alerta passou a
custar mais do que evitava.

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

| Mês | Pedidos | Taxa | PR-AUC 1ª execução | PR-AUC atual | PR-AUC / taxa | Custo (R$) | Nunca agir (R$) |
|---|---|---|---|---|---|---|---|
| 2018-01 | 7.069 | 5,7% | 0,102 | 0,125 | 2,2x | 27.615 | 24.180 |
| 2018-02 | 6.555 | 14,1% | 0,262 | 0,292 | 2,1x | 50.355 | 55.560 |
| 2018-03 | 7.003 | 19,0% | 0,308 | 0,372 | 2,0x | 67.740 | 79.680 |
| 2018-04 | 6.798 | 4,5% | 0,125 | 0,176 | 3,9x | 31.410 | 18.360 |
| 2018-05 | 6.749 | 6,6% | 0,137 | 0,166 | 2,5x | 36.390 | 26.580 |
| 2018-06 | 6.096 | 1,2% | 0,055 | 0,103 | 8,9x | 13.335 | 4.260 |
| 2018-07 | 6.156 | 3,4% | 0,075 | 0,092 | 2,7x | 36.930 | 12.480 |
| 2018-08 | 6.351 | 6,2% | 0,123 | 0,071 | 1,1x | 42.255 | 23.580 |

Três leituras:

- **A ordenação é estável:** de janeiro a julho, a PR-AUC fica entre 2 e 9 vezes a
  taxa base.
- **O alerta só se paga nos meses de crise:** fevereiro e março, os dois únicos
  com taxa acima de 14%.
- **Agosto é o ponto fraco:** a PR-AUC cai para quase o acaso (1,1x). É o mês em
  que o prazo médio prometido despencou para 15,8 dias, contra 23 a 28 antes, e
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

Na validação, o gradient boosting com o mês ficava abaixo da logística e até da
baseline (0,179). Sem o mês, ele empata com a logística, e o backtest melhora em
sete dos oito meses.

**Transparência sobre o teste.** A especificação manda usar o teste uma vez só.
Ele foi usado duas: a remoção do mês foi decidida depois de ver a primeira
execução inteira, teste incluído. A decisão se sustenta só com a validação e com
o argumento do `ano_compra`, mas quem lê os números do teste deve saber disso. A
PR-AUC no teste ficou praticamente igual nas duas execuções (0,087 e 0,085), o
que indica que a mudança não foi feita para melhorar o teste.

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

- **Taxa histórica por vendedor.** Provavelmente a feature mais forte que falta.
  Exige calcular "como era na data da compra", só com pedidos já entregues
  naquela data; feito errado, vira vazamento.
- **Limiar adaptativo ou por capacidade** (seção 5).
- **Mais de um ano de dados** antes de qualquer feature de calendário anual.
- **Recalibrar as probabilidades** numa janela recente.
- **Página no Looker** com os pedidos em andamento ordenados por risco.
- **Retreino agendado e alerta de drift.** Aqui o PSI é uma medição pontual,
  registrada neste documento, não monitoramento.
- **Censura:** pedidos sem entrega ficam fora do treino. São cerca de 2% por mês,
  então o viés é pequeno, mas existe.

## Como reproduzir

```bash
cd dbt && dbt build --profiles-dir . && cd ..
python -m ml.treinar      # grava ml/artefatos/modelo.joblib e metricas.json
python -m ml.inferir      # grava marts.previsao_atraso
cd dbt && dbt test --profiles-dir . --select source:ml_saida
```

Dependências em `requirements-ml.txt`. O CI roda os testes Python (`pytest
tests`), mas não o treino: os 800 pedidos da amostra não dão métrica que
signifique algo.
