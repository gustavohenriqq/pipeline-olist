# Etapa 4: previsão de atraso no ato da compra

Especificação de desenho. Data: 08/10/2026. Estado: aguardando revisão do dono.

## 1. Objetivo e uso

Prever, no momento em que o pedido é feito, a probabilidade de ele chegar depois
da data prometida ao cliente, e devolver essa previsão ao warehouse.

**Para que serve a previsão.** Proteger a satisfação. Um pedido marcado como risco
recebe uma ação preventiva (aviso ao cliente, prazo mais folgado ou frete
prioritário). A Etapa 2 mostrou o tamanho do problema: atrasar uma semana derruba
a nota de 4,29 para 2,72.

**O que precisa ficar visível no portfólio:** rigor. Auditoria de vazamento,
validação temporal, baseline antes do modelo e limiar escolhido por custo. Uma
métrica alta conseguida com vazamento vale menos que uma métrica modesta e honesta.

**Critérios de sucesso:**

1. Nenhuma feature usa informação posterior à compra, e isso é verificado por teste
   automático, não só por documento.
2. O modelo principal supera a baseline em PR-AUC no conjunto de teste. Se não
   superar, o documento diz isso, e esse é um resultado válido.
3. O limiar escolhido gera custo esperado menor que "não agir nunca" e que "agir
   sempre", sob a hipótese de custo declarada.
4. A tabela `marts.previsao_atraso` existe no Postgres local e no Neon, com testes
   dbt passando.
5. `docs/modelo-atraso.md` documenta resultados, premissas e limites.

## 2. O que os dados mostraram antes do desenho

Medido no Neon em 08/10/2026, pedidos entregues com data de entrega.

**Taxa de atraso instável mês a mês.** Perto de 3% em boa parte de 2017; 12,4% em
nov/2017 (Black Friday); 14,1% em fev/2018 e 19,0% em mar/2018; 1,2% em jun/2018.
Consequência: um único corte treino/teste pode cair num mês atípico. Por isso há
backtest mensal além do corte principal.

**Prazo prometido tem sinal forte e mudou no fim da série.**

| Prazo prometido | Pedidos | Atraso |
|---|---|---|
| 3 a 9 dias | 2.724 | 12,7% |
| 10 a 19 dias | 23.277 | 5,5% |
| 20 a 29 dias | 47.804 | 7,8% |
| 30 a 39 dias | 18.195 | 5,8% |
| 40 a 49 dias | 3.341 | 2,8% |
| 50 a 59 dias | 878 | 1,3% |

O prazo médio prometido caiu para 20,3 dias em jul/2018 e 15,8 dias em ago/2018,
contra 23 a 28 dias antes. É o tipo de mudança que o monitoramento de drift precisa
acusar.

**Censura no fim da série.** Em 2018, entre 71 e 161 pedidos por mês (cerca de 2%)
não foram entregues até o fim do dataset. Sem resposta conhecida, ficam fora do
treino e da avaliação. Pedidos de set e out/2018 (20 no total) não têm nenhuma
entrega e ficam fora.

**Um vendedor por pedido em 98% dos casos** (95.201 de 96.476 entregues). Atributos
de vendedor vêm do "vendedor principal": o de maior valor de itens no pedido.

## 3. Arquitetura

```
marts (fato_pedidos, fato_itens_pedido, dimensões)
        |
        v
dbt: ml.ml_features_atraso   (uma linha por pedido, só colunas permitidas)
        |
        v
Python: ml/treinar.py        (treina, avalia, escolhe limiar, salva modelo e métricas)
        |
        v
Python: ml/inferir.py        (pontua todos os pedidos)
        |
        v
marts.previsao_atraso        (lida pelo Looker via Neon; testada pelo dbt como source)
```

**Por que as features ficam no dbt.** A regra "só informação do ato da compra" é
uma regra de dados, e o projeto já testa regras de dados no dbt. Em SQL ela fica
versionada, revisável e com testes; o Python recebe uma tabela pronta e cuida só
do modelo.

**Por que a previsão é tabela própria.** Os fatos são incrementais com
`on_schema_change='fail'`: uma coluna nova exigiria `--full-refresh`. Além disso, o
modelo pode ser retreinado sem tocar no fato.

**Quem escreve o quê.** O dbt escreve `ml.ml_features_atraso`. O Python escreve
`marts.previsao_atraso`; o dbt só declara essa tabela como source e testa. O schema
`ml` não vai para o Neon, porque o publicador copia apenas o schema `marts`, e
`marts.previsao_atraso` é publicada automaticamente.

**Ordem de execução:** `dbt build` → `ml/treinar.py` → `ml/inferir.py` →
`dbt test --select source:ml_saida` → `scripts/publicar_marts.py`.

## 4. Dados de entrada: `ml.ml_features_atraso`

Model dbt em `dbt/models/ml/`, materializado como tabela no schema `ml`. Uma linha
por pedido com `purchased_at` entre 01/01/2017 e 31/08/2018 e status diferente de
cancelado ou indisponível.

**Colunas de controle (não são features):**

| Coluna | Uso |
|---|---|
| `pedido_sk` | chave para juntar a previsão ao fato |
| `order_id` | rastreio |
| `purchased_at` | separação temporal |
| `atrasou` | alvo: 1 se entregue depois da data prometida, 0 se no prazo, nulo se sem entrega |

**Features permitidas.** Todas existem no ato da compra.

| Feature | Origem | Observação |
|---|---|---|
| `prazo_prometido_dias` | `estimated_delivery_at - purchased_at` | o cliente vê a data no checkout |
| `cliente_uf`, `cliente_regiao` | cliente | |
| `vendedor_uf`, `vendedor_regiao` | vendedor principal | |
| `venda_interregional` | cliente x vendedor principal | |
| `distancia_km` | haversine entre CEPs | nulo quando o CEP não está na geolocalização |
| `valor_itens`, `valor_frete` | itens | |
| `frete_sobre_valor` | `valor_frete / valor_itens` | |
| `qtd_itens`, `qtd_vendedores_distintos`, `qtd_produtos_distintos` | itens | |
| `peso_total_g`, `volume_total_cm3` | produtos | |
| `categoria_grupo` | produto do item de maior valor | |
| `tipo_pagamento` | forma de maior valor | escolhida no checkout |
| `max_parcelas` | pagamentos | |
| `mes_compra`, `dia_semana_compra`, `hora_compra` | `purchased_at` | |

**Excluídas, e por quê:**

| Campo | Motivo |
|---|---|
| `approved_at` | acontece depois da compra (boleto pode levar dias) |
| `delivered_carrier_at`, `dias_ate_transportadora` | acontece depois da compra |
| `delivered_customer_at`, `tempo_entrega_dias`, `dias_em_transporte` | é o próprio desfecho |
| `atraso_dias`, `entregue_no_prazo` | é o alvo |
| `nota_avaliacao` | avaliação é posterior à entrega |
| `order_status`, `status_pedido`, `situacao_pedido` | status muda ao longo da vida do pedido |
| `valor_pago`, `qtd_pagamentos` | redundantes com valor e parcelas; evitados por simplicidade |
| `ano_compra` | o ano não se repete no futuro; com treino só em 2017 o modelo aprenderia uma constante |

A lista permitida fica numa constante única em `ml/features.py`, e um teste falha
se o modelo receber qualquer coluna fora dela.

## 5. Separação temporal

| Conjunto | Compras | Uso |
|---|---|---|
| Treino | jan a dez/2017 | ajuste dos modelos |
| Validação | jan a abr/2018 | escolha de hiperparâmetros e do limiar |
| Teste | mai a ago/2018 | avaliação final, usada uma única vez |

Pedidos de 2016 ficam fora: são 272 entregues e de um período de coleta irregular.

**Backtest mensal.** Para cada mês de jan a ago/2018: treina com todas as compras
anteriores a esse mês e avalia no mês. Reporta PR-AUC, taxa base e custo por mês. O
objetivo é mostrar estabilidade, não escolher nada; o corte principal continua
sendo o que decide.

## 6. Modelos

1. **Baseline:** taxa de atraso do treino por `cliente_uf`, usada como
   probabilidade. UF sem histórico recebe a taxa geral do treino.
2. **Regressão logística:** variáveis numéricas padronizadas, categóricas com
   one-hot, nulos imputados com a mediana do treino.
3. **Modelo principal:** `HistGradientBoostingClassifier` do scikit-learn, com
   categóricas nativas e nulos tratados pelo próprio modelo. Hiperparâmetros
   escolhidos numa grade pequena (taxa de aprendizado, profundidade, folhas
   mínimas) pela PR-AUC da validação.

`random_state` fixo em todos.

**Métricas:** PR-AUC (principal, porque a classe positiva é rara), ROC-AUC, Brier e
curva de calibração por decis. No limiar escolhido: precisão, recall, alertas por
mil pedidos e custo esperado.

**Experimento de sanidade do vazamento.** O modelo principal é treinado uma vez a
mais com `atraso_dias` incluído de propósito. O resultado (AUC perto de 1) vai para
o documento como demonstração do que o vazamento produz. Esse modelo não é salvo.

## 7. Limiar por custo

**Hipótese declarada:** ação preventiva custa R$ 15 por pedido marcado; atraso não
evitado custa R$ 60. A ação é tratada como eficaz quando aplicada a um pedido que
de fato atrasaria.

Custo esperado de um limiar = R$ 15 × (alertas) + R$ 60 × (atrasos não alertados).

O limiar é o que minimiza esse custo na **validação**, buscado numa grade de 0,01 a
0,99. No teste reporta-se o custo com esse limiar, comparado com "não agir nunca"
(R$ 60 × atrasos) e "agir sempre" (R$ 15 × pedidos).

**Sensibilidade:** limiar e custo recalculados para razões 1:2, 1:4 (a hipótese
central) e 1:8. Se a decisão mudar muito entre elas, o documento diz isso.

## 8. Inferência em lote: `marts.previsao_atraso`

O modelo final é o principal retreinado com treino e validação, usando o limiar
escolhido na validação.

| Coluna | Tipo | Descrição |
|---|---|---|
| `pedido_sk` | texto | chave do `fato_pedidos` |
| `prob_atraso` | numérico | entre 0 e 1 |
| `alerta` | booleano | `prob_atraso` maior ou igual ao limiar |
| `conjunto` | texto | `treino`, `validacao`, `teste` ou `em_andamento` |
| `limiar` | numérico | limiar usado |
| `modelo_versao` | texto | data e hash curto da lista de features |
| `gerado_em` | timestamp | |

`conjunto` existe para o dashboard não misturar previsões feitas sobre dados que o
modelo viu no treino com previsões honestas. `em_andamento` são pedidos dentro da
janela ainda sem entrega, os que interessam operacionalmente.

Escrita total e transacional (apaga e recria dentro de uma transação), no mesmo
padrão do publicador.

**Testes dbt na source:** `pedido_sk` único e não nulo; `prob_atraso` entre 0 e 1;
`conjunto` com valores aceitos; relacionamento com `fato_pedidos.pedido_sk`.

## 9. Drift

PSI (índice de estabilidade populacional) por feature, em 10 faixas definidas pelos
quantis do treino; categóricas por categoria. Duas comparações: treino contra
teste, e treino contra `em_andamento`. PSI acima de 0,2 é sinalizado no relatório.
A expectativa, pelos dados da seção 2, é que `prazo_prometido_dias` acuse.

Isso é medição pontual registrada no documento, não monitoramento agendado.

## 10. Código e organização

```
ml/
  __init__.py
  config.py       conexão (lê o .env como o resto do projeto), caminhos, custos, cortes de data
  dados.py        lê ml.ml_features_atraso do Postgres e separa os conjuntos
  features.py     lista permitida, colunas numéricas e categóricas, pré-processamento
  avaliacao.py    métricas, custo, escolha de limiar, sensibilidade, PSI
  treinar.py      CLI: baseline, logística, principal, backtest, sanidade; salva modelo e metricas.json
  inferir.py      CLI: carrega o modelo, pontua, escreve marts.previsao_atraso
  artefatos/      modelo.joblib e metricas.json (fora do Git; gerados)
tests/
  test_ml_features.py    lista permitida e ausência de colunas proibidas
  test_ml_avaliacao.py   custo, limiar, PSI em dados sintéticos
  test_ml_dados.py       cortes temporais sem sobreposição e sem 2016
dbt/models/ml/
  ml_features_atraso.sql
  _ml.yml               testes do model e source ml_saida.previsao_atraso
docs/modelo-atraso.md   resultados, premissas, limites
```

**Dependências:** `scikit-learn`, `numpy` e `joblib`, que já estão ou vêm com o
`requirements-extra.txt`. `matplotlib` só se a curva de calibração for gerada como
imagem. Sem dependência nova fora dessas.

**Makefile:** `ml-treinar`, `ml-inferir`.

**CI:** passo novo instalando `requirements-extra.txt` (só a parte de ML) e rodando
`pytest tests/`. O treino real não roda no CI: a amostra de 800 pedidos é pequena
demais para qualquer métrica significar algo. O model dbt `ml_features_atraso` roda
no CI junto do resto do `dbt build`.

## 11. Erros e casos de borda

- **Distância nula** (CEP fora da geolocalização, 278 clientes): fica nula; o modelo
  principal trata nativamente, a logística imputa a mediana.
- **Categoria nula** ("Não informada" no dbt): vira uma categoria normal.
- **UF da validação ou teste sem histórico no treino** (baseline): taxa geral.
- **Categoria nova no teste** (modelos): tratada como desconhecida pelo
  pré-processamento, sem erro.
- **`inferir.py` sem modelo treinado:** falha com mensagem dizendo para rodar
  `treinar.py` antes.
- **Banco local fora do ar:** mesma mensagem de erro de conexão dos outros scripts.

## 12. Fora do escopo

- Página nova no Looker com os pedidos em risco (próximo passo natural, manual).
- Taxa histórica de atraso por vendedor. Exige cálculo "como era na data da
  compra", considerando só pedidos já entregues naquela data; fazer errado é
  vazamento. Fica registrada como próxima melhoria.
- Retreino agendado e alertas automáticos de drift.
- Previsão em tempo real ou serviço de API.

## 13. Riscos

- **A hipótese de custo é inventada.** Mitigação: declarada em destaque e com
  sensibilidade.
- **Mudança de regime no teste** (taxa de 1,2% em jun/2018 e prazos mais curtos):
  o desempenho no teste pode cair em relação à validação. Isso é informação, não
  falha; o documento explica com o backtest e o PSI.
- **Previsões sobre o treino parecem melhores do que são.** Mitigação: coluna
  `conjunto` e aviso no documento.
- **Seleção por censura:** pedidos sem entrega ficam fora do treino. Como são cerca
  de 2% por mês, o viés é pequeno, mas é registrado.
