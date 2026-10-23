# Atraso na entrega: quanto custa e onde agir

Análise sobre 96.478 pedidos entregues do dataset Olist (set/2016 a out/2018).
Todos os números saem das marts do projeto e são reproduzíveis pelas queries no
final do documento.

---

## Resumo executivo

**O problema.** Atrasar a entrega em uma semana derruba a nota do cliente de
**4,29 para 2,72**. Entre 8 e 30 dias de atraso, a nota cai para **1,65**. São
6.534 pedidos atrasados, R$ 1.150.892 em receita, 7,3% do total.

**Onde agir, e aqui a leitura óbvia está errada.** O Sudeste concentra 4.049 dos
6.534 atrasos, 62% do total. A conclusão natural seria priorizar o Sudeste. Mas
o Sudeste tem **6,1% de taxa de atraso contra 6,8% da média nacional**: ele tem
mais atrasos porque tem mais pedidos, não porque atrasa mais. Corrigindo pelo
volume, o Sudeste tem **434 atrasos a menos** do que se esperaria.

O problema real tem **dois endereços**, e o segundo só aparece no nível de
estado: o **Rio de Janeiro**, sozinho, gera **659 atrasos em excesso**, e os nove
estados do **Nordeste** somam **537**. Juntos, respondem por 86% de todo o atraso
em excesso do país.

> **Correção.** Uma versão anterior deste documento afirmava que o Nordeste
> respondia por 94% do atraso em excesso. A conta estava certa no nível de
> região e errada como conclusão: agregando por região, o excesso do Rio de
> Janeiro (+659) ficava escondido dentro do Sudeste, compensado pelo desempenho
> de São Paulo (-923). O erro apareceu quando um mapa por estado pediu um grão
> mais fino. Detalhe na seção 2.1.

**De quem é o atraso.** Decompondo o tempo de entrega, **87% do atraso nasce no
transporte e apenas 13% no vendedor**. E nos pedidos atrasados do Nordeste, o
vendedor é o mais rápido do país (4,8 dias contra 6,5 do Sudeste). Os vendedores
que atendem a região despacham acima da média e mesmo assim o pedido chega
atrasado.

**Recomendação.** Priorizar **malha logística** para o **Rio de Janeiro** e os
estados do **Nordeste**, não cobrança de SLA de vendedor. Trazer esses dez
estados para a média nacional eliminaria cerca de 1.196 atrasos, associados a
**R$ 224 mil** em receita (R$ 111 mil no RJ e R$ 114 mil no Nordeste), e evitaria
a queda de 2,6 pontos de nota nesses pedidos. No RJ o padrão se repete: o
vendedor despacha mais rápido que a média (5,2 dias contra 6,3) e o transporte é
mais lento (32,7 dias contra 26,4).

Vale notar o que essa conclusão evita: a ação intuitiva seria cobrar os
vendedores da região com pior indicador. Os dados mostram que isso atacaria
justamente a parte que já funciona melhor que a média, gastando esforço sem mover
o resultado.

> **Atualização (23/10/2026).** A recomendação acima vale inteira para o RJ e
> só em parte para o Nordeste. Separando prazo prometido curto de entrega lenta
> (seção 7), 88% do excesso do RJ (577 de 659) é entrega lenta, mas 88% do
> excesso do Nordeste (475 de 537) é prazo curto: a entrega é normal para a
> distância, e a promessa cobre menos do tempo típico da rota do que no resto do
> país. Para o Nordeste, a primeira alavanca é a estimativa de prazo; encurtar o
> tempo típico com malha logística é a outra saída. O texto original foi mantido.

---

## 1. O achado: atraso destrói a nota

| Situação da entrega | Pedidos | Nota média | % de 1 estrela | % de 5 estrelas |
|---|---|---|---|---|
| No prazo | 89.936 | **4,29** | 6,6% | 62,3% |
| Atraso de 1 a 7 dias | 3.672 | 2,72 | 41,4% | 23,9% |
| Atraso de 8 a 30 dias | 2.517 | **1,65** | 70,8% | 6,1% |
| Atraso acima de 30 dias | 345 | 2,06 | 63,2% | 13,7% |

A queda não é gradual: basta **um dia** de atraso para a nota despencar. Entre a
faixa "no prazo" e a faixa "1 a 7 dias", a proporção de avaliações 1 estrela
salta de 6,6% para 41,4%.

### O efeito é robusto, não é composição regional

Uma objeção legítima: e se o atraso apenas acompanhar regiões que já avaliam
pior? Controlando por região, o efeito persiste em todas as cinco, com magnitude
praticamente idêntica:

| Região | No prazo | 1 a 7 dias | 8 a 30 dias | Queda |
|---|---|---|---|---|
| Centro-Oeste | 4,26 | 2,52 | 1,71 | 2,55 |
| Nordeste | 4,23 | 2,67 | 1,66 | 2,57 |
| Norte | 4,20 | 2,75 | 1,46 | 2,74 |
| Sudeste | 4,30 | 2,73 | 1,63 | 2,67 |
| Sul | 4,30 | 2,80 | 1,70 | 2,60 |

A queda varia entre 2,55 e 2,74 pontos. Se o efeito fosse artefato de
composição, ele desapareceria ou variaria muito dentro dos grupos. Não é o caso.

**Ressalva honesta:** isto é controle por um fator, não identificação causal. A
relação pode ainda ser confundida por vendedor, categoria ou distância. O que se
pode afirmar é que a associação é forte, consistente e não explicada por região.

---

## 2. Onde agir: excesso, não volume

Comparar volume absoluto de atraso entre regiões de tamanhos diferentes leva à
conclusão errada. A pergunta certa é: **quantos atrasos a mais do que o esperado
cada região produz**, dada a taxa nacional de 6,8%.

| Região | Entregues | Atrasos | Esperado | Excesso | Receita evitável |
|---|---|---|---|---|---|
| **Nordeste** | 9.049 | 1.150 | 613 | **+537** | **R$ 112.096** |
| Norte | 1.797 | 154 | 122 | +32 | R$ 7.507 |
| Centro-Oeste | 5.625 | 366 | 381 | -15 | — |
| Sul | 13.817 | 815 | 936 | -121 | — |
| Sudeste | 66.190 | 4.049 | 4.483 | -434 | — |

No nível de região, o Nordeste parece responder por 94% do atraso em excesso, e
Sudeste, Sul e Centro-Oeste parecem operar abaixo da média. **A seção seguinte
mostra por que essa leitura está incompleta.**

### 2.1 O nível de região escondia o maior foco do país

A mesma conta, feita por estado:

| UF | Região | Entregues | Taxa | Excesso | Receita evitável |
|---|---|---|---|---|---|
| **RJ** | Sudeste | 12.344 | 12,1% | **+659** | **R$ 110.872** |
| BA | Nordeste | 3.256 | 12,2% | +175 | |
| CE | Nordeste | 1.281 | 13,7% | +89 | |
| ES | Sudeste | 1.994 | 10,7% | +79 | R$ 14.881 |
| MA | Nordeste | 716 | 17,5% | +77 | |
| AL | Nordeste | 397 | 21,4% | +58 | |
| ... | | | | | |
| MG | Sudeste | 11.352 | 4,6% | -249 | |
| **SP** | Sudeste | 40.500 | 4,5% | **-923** | |

Somando só os estados que atrasam acima da média:

| Grupo | Excesso | Participação | Receita evitável |
|---|---|---|---|
| **Rio de Janeiro** | 659 | **47%** | R$ 110.872 |
| **Nordeste** (os 9 estados) | 537 | **38%** | R$ 113.581 |
| Espírito Santo | 79 | 6% | R$ 14.881 |
| Outros (MS, PA, RR, SC, TO) | 124 | 9% | R$ 23.492 |
| **Total** | **1.399** | 100% | **R$ 262.826** |

**O Rio de Janeiro sozinho tem mais atraso em excesso que o Nordeste inteiro.**
Na visão por região, ele desaparece porque São Paulo, com 40.500 pedidos
entregues e taxa de 4,5%, gera 923 atrasos a menos que o esperado e compensa o
RJ dentro do mesmo balde "Sudeste". O saldo da região fica negativo (-434) e o
foco some.

É um erro clássico de agregação: o total do grupo pode esconder um membro ruim
quando outro membro muito maior é muito bom. A lição de método vale mais que o
número: **excesso precisa ser calculado no grão mais fino disponível e só depois
agregado**, nunca o contrário.

Os nove estados do Nordeste têm excesso positivo, então para essa região a conta
por região e por estado coincide. O que muda a conclusão é exclusivamente o RJ.

### Um fator agravante identificado

Venda entre regiões diferentes atrasa **7,5%** contra **6,0%** de venda dentro da
mesma região, um aumento relativo de 25%. Como o Nordeste tem poucos vendedores
locais, boa parte de seus pedidos vem de fora, o que é consistente com a taxa
mais alta. Confirmar essa cadeia causal exige a decomposição do tempo de entrega
descrita na seção 5.

---

## 3. A anomalia da cauda

A curva de nota por atraso **não é monótona**. Pedidos com mais de 30 dias de
atraso têm nota 2,06, melhor que os de 8 a 30 dias (1,65). Isso é
contraintuitivo e merecia investigação.

### Hipótese 1: viés de resposta. Descartada.

Se clientes muito prejudicados simplesmente parassem de responder à pesquisa, a
média subiria artificialmente. A taxa de resposta de fato cai com o atraso, mas
pouco:

| Faixa | Taxa de resposta |
|---|---|
| No prazo | 99,5% |
| 1 a 7 dias | 98,0% |
| 8 a 30 dias | 97,4% |
| Mais de 30 dias | 95,4% |

Uma queda de 2 pontos percentuais entre as duas últimas faixas não sustenta uma
recuperação de 0,41 ponto na nota média. Hipótese insuficiente.

### O que realmente explica: mais notas 5, não menos notas 1

| Faixa | 1 estrela | 5 estrelas |
|---|---|---|
| 8 a 30 dias | 70,8% | 6,1% |
| Mais de 30 dias | 63,2% | **13,7%** |

A faixa acima de 30 dias tem **mais que o dobro** de avaliações máximas. Como a
amostra é pequena (329 avaliações), testei se a diferença sobrevive ao acaso:

```
8 a 30 dias :  150/2452 =  6,1%   IC95% [5,2%, 7,1%]
mais de 30  :   45/329  = 13,7%   IC95% [10,0%, 17,4%]

teste z de duas proporções: z = 5,04   p = 4,6e-07
```

Os intervalos não se sobrepõem e o p-valor é da ordem de 10⁻⁷. **A diferença é
real.** Existe um subgrupo de clientes extremamente atrasados que avalia com
nota máxima.

### Interpretação, e o que falta para fechar

A explicação mais provável é **resolução do caso**: pedidos que atrasam meses
tendem a passar por atendimento, reenvio ou reembolso, e o cliente avalia o
desfecho, não a espera. O dataset não tem tabela de atendimento nem de reembolso,
então **esta hipótese não é testável com os dados disponíveis** e fica registrada
como tal, não como conclusão.

O que se pode afirmar com segurança: a recuperação existe, é estatisticamente
sólida, e vem de notas 5, não da ausência de notas 1.

---

## 4. O que foi testado e descartado

**Análise de coorte e retenção.** É o reflexo automático em e-commerce, e não é
viável aqui: apenas **3,1% dos clientes compraram mais de uma vez** (93.099 de
96.096 clientes têm um único pedido). Sem recompra não há coorte, e qualquer
curva de retenção seria ruído. Registrado como achado.

Isso tem uma consequência importante para a leitura do custo do atraso: **não é
possível medir o efeito do atraso sobre recompra neste dataset**. O custo
estimado aqui é de receita em risco e de satisfação, não de perda de cliente ao
longo do tempo. Um relatório que afirmasse "o atraso custa X em churn" estaria
inventando.

---

## 5. De quem é o atraso: do vendedor ou da transportadora

A pergunta anterior deixava a recomendação incompleta. Saber **onde** o atraso
acontece não diz **quem** o causa, e a ação muda por completo: se o gargalo é o
vendedor, a resposta é SLA de despacho e onboarding; se é a transportadora, é
malha logística.

O tempo total de entrega se decompõe em duas partes:

- **Tempo do vendedor:** da compra até a entrega do pacote à transportadora.
- **Tempo do transporte:** da coleta até a entrega ao cliente.

| Situação | Pedidos | Tempo do vendedor | Tempo de transporte | Total |
|---|---|---|---|---|
| No prazo | 89.936 | 3,0 dias | 7,9 dias | 10,9 dias |
| Atrasado | 6.533 | 6,0 dias | **27,9 dias** | 33,9 dias |
| **Diferença** | | **+3,0 dias** | **+19,9 dias** | +23,0 dias |

**87% do atraso nasce no transporte, 13% no vendedor.**

### O corte por região elimina a hipótese do vendedor

O dado mais claro é a estabilidade do tempo do vendedor. Entre pedidos entregues
no prazo, ele é praticamente idêntico em todo o país:

| Região | Vendedor (no prazo) | Transporte (no prazo) | Vendedor (atrasado) | Transporte (atrasado) |
|---|---|---|---|---|
| Sudeste | 3,0 dias | 6,4 dias | 6,5 dias | 24,6 dias |
| Sul | 3,1 dias | 9,6 dias | 5,9 dias | 29,1 dias |
| Centro-Oeste | 3,0 dias | 10,6 dias | 5,6 dias | 28,6 dias |
| Nordeste | 3,1 dias | 13,8 dias | **4,8 dias** | **36,1 dias** |
| Norte | 3,2 dias | 16,9 dias | 4,9 dias | **43,3 dias** |

O vendedor despacha em cerca de 3 dias em qualquer região. O transporte varia de
**6,4 dias no Sudeste a 16,9 dias no Norte**, quase o triplo, e o mesmo padrão se
amplifica nos pedidos atrasados.

E o detalhe que fecha o caso: nos pedidos atrasados do **Nordeste**, o vendedor é
o **mais rápido de todos** (4,8 dias, contra 6,5 do Sudeste). Os vendedores que
atendem o Nordeste despacham mais rápido que a média e ainda assim os pedidos
chegam atrasados. O problema não está neles.

O **Rio de Janeiro**, que a seção 2.1 mostrou ser o maior foco de excesso do país,
repete o padrão: nos pedidos atrasados, o vendedor leva 5,2 dias (contra 6,3 no
resto do país) e o transporte leva **32,7 dias** (contra 26,4). Os dois focos têm
a mesma causa.

### Recomendação revisada

A ação é **logística, não comercial**. Cobrar SLA de despacho dos vendedores do
Nordeste atacaria a parte que já funciona melhor que a média e não moveria o
indicador. O investimento precisa ir para malha de distribuição e prazo de
transporte nas rotas para o **Rio de Janeiro** e o **Nordeste**, que juntos
concentram 86% do atraso em excesso do país.

Isso também corrige a leitura do prazo prometido: se o transporte para o Norte
leva 16,9 dias mesmo quando dá certo, parte do "atraso" pode ser prazo estimado
mal calibrado para a região, e não falha de execução. Separar essas duas causas é
o próximo recorte natural.

> **Atualização (23/10/2026).** O recorte foi feito na seção 7. O que esta seção
> mostra se mantém (o vendedor não é o gargalo, o tempo a mais está no
> transporte), e a recomendação de malha logística se mantém para o RJ. Para o
> Nordeste ela estava incompleta: 88% do excesso da região é prazo prometido
> curto para a rota, não entrega fora do padrão da rota.

> **Nota de método.** Esta seção é um caso de pergunta de negócio dirigindo a
> modelagem, e não o contrário. Os campos `approved_at` e `delivered_carrier_at`
> existiam no staging desde o início, mas não haviam sido promovidos ao
> `fato_pedidos` porque nenhuma pergunta os exigia. A análise pediu, o modelo
> mudou: `dias_ate_transportadora` e `dias_em_transporte` agora são colunas
> testadas da mart.

### Qualidade de dado encontrada no caminho

Ao promover os campos, 22 pedidos se revelaram impossíveis: 2 com a
transportadora recebendo o pacote **antes** da compra e 20 com o cliente
recebendo **antes** da transportadora coletar. O extremo chega a -171 dias.

São 0,02% da base e não afetam as conclusões acima. Na primeira versão ficaram
só registrados como dois testes em **aviso** no `_marts.yml`, junto do gap de
geolocalização, com a decisão de tratamento adiada.

**Decisão (23/10/2026): anular só os dois campos de tempo, com flag.** Nos 22
pedidos, compra, entrega ao cliente e prazo prometido são coerentes entre si
(todos foram entregues, e no prazo); o carimbo errado é sempre a data de coleta
(`delivered_carrier_at`). As três opções comparadas:

| Opção | O que acontece | Por que sim ou não |
|---|---|---|
| Manter com flag | Valores negativos seguem na mart, com uma coluna marcando o caso | Cada consumidor (Power BI, painel, agente, Looker) precisaria lembrar de filtrar. Uma média de vendedor ou de rota pequena sai puxada por um -171 ao lado de um 178 |
| **Anular só os campos de tempo** | `dias_ate_transportadora` e `dias_em_transporte` ficam nulos nos 22; a flag `coleta_fora_de_ordem` marca o caso | Média ignora nulo, então nenhum consumidor precisa saber da regra. Receita, nota, prazo e atraso dos 22 pedidos continuam contando, porque estão certos |
| Excluir da mart | Os 22 pedidos somem do `fato_pedidos` | Joga fora venda, nota e entrega que estão corretas. Muda a contagem de pedidos (99.441) e a receita usadas no Power BI, no painel e no modelo de previsão, por causa de um carimbo só |

A data de coleta original continua no fato (`delivered_carrier_at`) para
auditoria. A regra compara em **dias**, como as métricas: pelo horário seriam
189 casos, mas 167 deles caem no mesmo dia (coleta em média 0,7 h "antes" da
compra, cara de fuso ou carimbo em lote) e dão 0 dia, sem distorcer média.

Testes: os dois `valor_minimo` passaram de aviso para **erro** (valor negativo
agora é bug, não dado conhecido); a flag tem `not_null`; o teste em aviso
`assert_coleta_fora_de_ordem_conhecida` lista os 22 pedidos a cada build; e o
teste singular `assert_coleta_fora_de_ordem_anulada` garante que flag e campos
nulos andam juntos, nos dois sentidos.

**Números desta seção conferidos depois da mudança: nenhum valor publicado
mudou.** Os 22 pedidos estão todos em "no prazo", diluídos em 89.936. Na base
desta seção (pedidos `delivered` com coleta e entrega registradas), a média do
vendedor no prazo fica em 3,009 dias antes e depois, a do transporte vai de
7,932 para 7,933, e os 87% do atraso no transporte (86,83%) não se movem. Por
região, só Sudeste (19 casos) e Sul (3) mexem, na terceira casa (Sul,
transporte no prazo: 9,586 para 9,588). Os pedidos atrasados, o Rio de Janeiro
e o resto do país não têm nenhum dos 22. A coluna "Pedidos" da primeira tabela
continua 89.936, mas a decomposição no prazo passa a usar 89.914 pedidos.

---

## 6. Limitações

**Outras limitações:**

- Dataset histórico e fechado (2016 a 2018). Não há como validar se as conclusões
  se sustentam hoje.
- A associação entre atraso e nota é forte e robusta a região, mas não é prova
  causal. Vendedor, categoria e distância continuam como confundidores possíveis.
- 278 CEPs de cliente não existem na base de geolocalização, o que limita
  análises de distância.

---

## 7. Prazo curto ou entrega lenta

A seção 5 terminou com uma pergunta aberta: se o transporte para o Norte leva
16,9 dias mesmo quando dá certo, parte do atraso pode ser promessa errada, e não
falha de execução. A ação muda com a causa. Prazo curto se resolve recalibrando a
estimativa; entrega lenta, na malha logística.

**Resposta curta: os dois focos têm causas diferentes.** No **Rio de Janeiro**,
**88% do excesso** (577 de 659 atrasos) é **entrega lenta**: a promessa segue a
régua do país, e o que falha é uma cauda de pedidos que demoram mais de 2,21 vezes
o tempo típico da rota. No **Nordeste**, **88% do excesso** (475 de 537) é
**prazo curto**: as entregas se comportam como as de qualquer rota longa, mas a
promessa cobre menos do tempo típico da rota (1,4 a 2,0 vezes, contra 2,21 no
país).

> **O que isso corrige.** A seção 5 e o resumo executivo recomendam malha
> logística para o RJ e para o Nordeste. Para o RJ, a recomendação se mantém.
> Para o Nordeste, ela estava incompleta: a alavanca principal é a estimativa de
> prazo, não a execução da entrega. Os números das seções anteriores não mudam.

### 7.1 Folga por UF: folga parecida, taxas muito diferentes

Folga é o prazo prometido menos o tempo real de entrega (o `atraso_dias` com o
sinal trocado). Base: 96.470 pedidos entregues com data de entrega.

| UF | Entregues | Prazo médio | Tempo médio | Folga média | Prazo / tempo típico | Acima do padrão | Taxa de atraso |
|---|---|---|---|---|---|---|---|
| AL | 397 | 33,2 | 24,5 | 8,7 | 1,39 | 2,0% | **21,4%** |
| MA | 716 | 31,1 | 21,5 | 9,6 | 1,55 | 4,2% | 17,5% |
| SE | 338 | 31,5 | 21,4 | 10,1 | 1,71 | 7,1% | 15,1% |
| PI | 476 | 30,7 | 19,4 | 11,3 | 1,82 | 5,0% | 13,9% |
| CE | 1.281 | 32,0 | 21,2 | 10,8 | 1,76 | 7,6% | 13,7% |
| BA | 3.256 | 30,1 | 19,3 | 10,8 | 1,72 | 4,6% | 12,2% |
| **RJ** | 12.344 | 27,0 | 15,2 | **11,8** | 2,08 | **11,3%** | **12,1%** |
| PB | 515 | 33,7 | 20,4 | 13,3 | 1,79 | 4,5% | 10,3% |
| PE | 1.596 | 31,7 | 18,4 | 13,3 | 2,00 | 7,2% | 9,6% |
| RN | 474 | 32,9 | 19,2 | 13,6 | 1,88 | 6,5% | 9,3% |
| RS | 5.346 | 29,2 | 15,2 | 13,9 | 2,14 | 6,8% | 6,1% |
| MG | 11.352 | 25,2 | 11,9 | 13,2 | 2,27 | 5,9% | 4,6% |
| **SP** | 40.493 | 19,8 | 8,7 | **11,1** | 2,57 | 7,7% | **4,5%** |
| PR | 4.923 | 25,3 | 11,9 | 13,3 | 2,36 | 6,2% | 4,0% |
| **Brasil** | 96.470 | | | | 2,21 | 7,3% | 6,8% |

Prazo e tempo em dias. "Prazo / tempo típico" é a mediana, por pedido, do prazo
prometido dividido pelo tempo típico da rota (7.3). "Acima do padrão" é a parcela
dos pedidos que levou mais de 2,21 vezes o tempo típico da rota. A tabela completa,
com as 27 UFs, sai da primeira query de 7.8.

O que a issue pedia para ver aparece na primeira linha que se compara: **o RJ tem
folga média maior que São Paulo** (11,8 contra 11,1 dias) e **atrasa 2,7 vezes
mais** (12,1% contra 4,5%). Folga média não explica a taxa. Duas coisas
explicam, e cada foco tem uma delas:

- **Nordeste: a promessa é curta para a rota.** Em Alagoas o prazo prometido é
  1,39 vez o tempo típico da rota; no país, 2,21. Mas a parcela de entregas fora
  do padrão é baixa (2,0% em AL, 4,2% no MA, contra 7,3% no país).
- **RJ: a promessa é normal e a cauda é longa.** O prazo é 2,08 vezes o tempo
  típico, perto do país, mas 11,3% das entregas passam de 2,21 vezes o tempo
  típico, a maior parcela entre as UFs com volume.

Uma comparação que costuma aparecer, "o RJ recebe prazo 2,2 dias menor que o RS"
(27,0 contra 29,2), é verdadeira e não aponta a causa: o RJ está mais perto dos
vendedores (SP>RJ tem tempo típico de 13 dias, SP>RS de 14), e a promessa relativa
é quase a mesma (2,08 contra 2,14). O que separa os dois é a cauda: 11,3% acima
do padrão no RJ, 6,8% no RS.

### 7.2 Por rota: a régua precisa ser proporcional

Rota é a UF do vendedor seguida da UF do cliente. Rotas com 250 pedidos ou mais,
selecionadas (a lista completa, com 44 rotas, sai da segunda query de 7.8):

| Rota | Entregues | Prazo médio | Tempo típico | p90 do tempo | Prazo / típico | p90 / típico | Folga média | Taxa de atraso |
|---|---|---|---|---|---|---|---|---|
| SP>SP | 30.644 | 17,9 | 7 | 14 | 2,56 | 2,00 | 10,1 | 4,7% |
| SP>MG | 7.414 | 25,0 | 11 | 21 | 2,27 | 1,91 | 12,7 | 5,3% |
| SP>PR | 3.110 | 25,8 | 11 | 21 | 2,34 | 1,91 | 13,0 | 4,4% |
| SP>RS | 3.581 | 30,3 | 14 | 27 | 2,16 | 1,93 | 14,2 | 6,6% |
| **SP>RJ** | 8.124 | 27,0 | 13 | **31** | 2,08 | **2,38** | 10,8 | **14,2%** |
| MG>RJ | 1.126 | 27,5 | 11 | 25 | 2,50 | 2,27 | 13,3 | 8,3% |
| PR>RJ | 956 | 30,3 | 14 | 33,5 | 2,17 | 2,39 | 13,0 | 12,2% |
| SP>PE | 1.132 | 32,5 | 16 | 31 | 2,03 | 1,94 | 13,6 | 9,8% |
| SP>CE | 967 | 32,1 | 18 | 34 | **1,78** | 1,89 | 10,9 | 13,8% |
| SP>BA | 2.303 | 30,5 | 18 | 32 | **1,69** | 1,78 | 10,7 | 12,9% |
| SP>MA | 489 | 31,3 | 20 | 35 | **1,57** | 1,75 | 9,3 | 19,0% |
| SP>AL | 255 | 32,9 | 23 | 41 | **1,43** | 1,78 | 7,9 | **23,9%** |

Tempo típico é a mediana do tempo real de entrega da rota, em dias. Aqui,
"prazo / típico" é o prazo médio da rota dividido pelo tempo típico. O par que resume
a seção: **SP>RJ e SP>MG** têm tempo típico parecido (13 e 11 dias) e prazo
parecido (27 e 25 dias), mas o p90 do RJ é 31 dias contra 21. **SP>AL** tem a
cauda de uma rota normal (p90 de 1,78 vez o típico) e uma promessa de só 1,43 vez
o típico.

**Por que proporcional, e não em dias.** A primeira versão desta regra usou uma
régua em dias (prazo padrão = tempo típico + 13 dias, a mediana nacional da
diferença). Ela dava ao Nordeste só 26% de prazo curto. Mas a dispersão do tempo
de entrega cresce com o tempo típico da rota, então uma folga fixa em dias é mais
apertada para rota longa e acaba contando como "entrega lenta" a variação normal
de quem mora longe. Entre as 63 rotas com 100 pedidos ou mais (fora as que vão
para o RJ):

| Tempo típico da rota | Rotas | Entregues | p90 menos típico | p90 / típico |
|---|---|---|---|---|
| Até 8 dias | 9 | 34.408 | 7,2 dias | 1,99 |
| 9 a 12 dias | 23 | 24.627 | 9,2 dias | 1,86 |
| 13 a 16 dias | 20 | 13.632 | 11,8 dias | 1,82 |
| 17 dias ou mais | 11 | 6.208 | 16,0 dias | 1,85 |
| *Rotas para o RJ, 9 a 16 dias* | 5 | 10.914 | 14,5 a 17,5 dias | **2,31 a 2,32** |

Em dias, a dispersão acompanha o tempo típico (correlação de **0,88**; cada dia
de tempo típico traz 0,74 dia a mais de cauda). Em razão, ela fica estável em
torno de 1,85 (correlação de -0,34). A régua proporcional é a que trata rota
curta e rota longa do mesmo jeito. E as rotas para o RJ são as únicas fora do
padrão: na mesma faixa de tempo típico, a cauda é 2,3 vezes o típico, contra 1,8
a 1,9 nas demais.

### 7.3 A regra

Para cada pedido entregue com data de entrega:

1. **Tempo típico da rota:** mediana do tempo real de entrega dos pedidos da
   mesma rota. Rota com menos de 30 pedidos, ou pedido com vendedores em mais de
   uma UF, usa a mediana da UF do cliente (2.678 pedidos, 2,8%, dos quais 509
   com vendedores em mais de uma UF).
2. **Prazo padrão:** tempo típico vezes **2,21**, a mediana nacional de prazo
   prometido sobre tempo típico, arredondada em duas casas. É a promessa que o
   pedido teria se a rota seguisse a régua das outras.
3. **Classificação do pedido atrasado:**
   - **prazo curto:** chegou dentro do prazo padrão. Com a promessa padrão, ele
     estaria no prazo; a promessa que recebeu era menor que a régua do país.
   - **entrega lenta:** passou do prazo padrão. Atrasaria mesmo com a promessa
     padrão; a entrega demorou mais de 2,21 vezes o que a rota costuma demorar.

A regra virou o model `marts.prazo_vs_entrega` (uma linha por pedido entregue com
data), com a coluna `causa_atraso` e as colunas intermediárias (`rota`,
`tempo_tipico_dias`, `prazo_padrao_dias`, `folga_dias`), para o BI e o agente
usarem a mesma classificação. Testes: chave única e ligada ao `fato_pedidos`,
valores aceitos de `causa_atraso` e `referencia_tipico`, e dois testes
singulares. Um confere que a tabela tem exatamente os pedidos entregues com data
do fato. O outro, que a causa bate com a regra, só existe em pedido atrasado e
que a folga é o `atraso_dias` com sinal trocado.

**Um erro que a conferência pegou.** Na primeira versão do model, a razão padrão
era a mediana sem arredondar: 31/14 em ponto flutuante. A query independente
(de `obt_pedidos`, sem passar pelo model) discordou em 39 pedidos, todos na
fronteira, com tempo exatamente igual ao prazo padrão (14 × 31/14 = 31 dias):
a classe dependia da 15ª casa decimal. Com a razão arredondada em 2,21, as duas
contas concordam nos 96.470 pedidos.

### 7.4 Quanto do excesso vem de cada causa

No país, os 6.534 atrasos se dividem em **2.220 por prazo curto** (2,30% dos
entregues) e **4.314 por entrega lenta** (4,47%). O excesso de cada causa é
calculado como na seção 2: atrasos daquela causa menos os que se esperariam com a
taxa nacional da mesma causa, por UF, e só depois somados. Como as duas taxas
somam a taxa nacional, os dois excessos somam o excesso da seção 2.1.

| Foco | Entregues | Atrasos | Prazo curto | Entrega lenta | Excesso | Excesso por prazo curto | Excesso por entrega lenta |
|---|---|---|---|---|---|---|---|
| **RJ** | 12.344 | 1.495 | 366 | 1.129 | **+659** | +82 (12%) | **+577 (88%)** |
| **Nordeste** (9 UFs) | 9.049 | 1.150 | 683 | 467 | **+537** | **+475 (88%)** | +62 (12%) |
| BA | 3.256 | 396 | 256 | 140 | +175 | +181 | -6 |
| CE | 1.281 | 176 | 81 | 95 | +89 | +52 | +38 |
| MA | 716 | 125 | 96 | 29 | +77 | +80 | -3 |
| AL | 397 | 85 | 77 | 8 | +58 | +68 | -10 |
| PE | 1.596 | 154 | 51 | 103 | +46 | +14 | +32 |
| PI | 476 | 66 | 43 | 23 | +34 | +32 | +2 |
| SE | 338 | 51 | 28 | 23 | +28 | +20 | +8 |
| PB | 515 | 53 | 33 | 20 | +18 | +21 | -3 |
| RN | 474 | 44 | 18 | 26 | +12 | +7 | +5 |

Entregues como na seção 2.1 (inclui os 8 pedidos entregues sem data, que não
contam como atraso). Excesso arredondado por linha; a linha do Nordeste soma as
UFs antes de arredondar.

Dentro do Nordeste o padrão não é uniforme. Bahia, Maranhão e Alagoas, que somam
310 dos 537, são quase só prazo curto (a entrega lenta fica abaixo do esperado).
Pernambuco é o contrário: dos +46, +32 vêm de entrega lenta. Ceará fica no meio.

E no RJ a entrega lenta é transporte, como a seção 5 mostrou para o atraso todo:
nos 1.129 pedidos de entrega lenta, o vendedor leva 5,5 dias (3,0 nos pedidos no
prazo) e o transporte **36,9 dias** (9,1 no prazo). Dos 30,3 dias a mais, 27,8
(92%) estão no transporte.

### 7.5 Sensibilidade à régua

A divisão depende da régua. A mesma conta com os quartis da razão nacional (1,83
e 2,73) e com a régua em dias que 7.2 descartou:

| Régua | RJ: prazo curto | RJ: entrega lenta | Nordeste: prazo curto | Nordeste: entrega lenta |
|---|---|---|---|---|
| Razão 1,83 (1º quartil) | -16 | +675 | +288 (54%) | +249 |
| **Razão 2,21 (mediana, a regra)** | **+82** | **+577 (88%)** | **+475 (88%)** | **+62** |
| Razão 2,73 (3º quartil) | +246 | +413 (63%) | +591 | -54 |
| Dias: típico + 13 (descartada) | +35 | +624 (95%) | +142 (26%) | +395 |

O que não muda com a régua: **no RJ, entrega lenta é a maior parte do excesso
em todas as quatro** (63% a mais de 100%). No Nordeste, **prazo curto é a maior
parte em todas as réguas proporcionais** (54% a mais de 100%) e só perde na
régua em dias, que trata como lenta a variação normal de rota longa. Valor
negativo quer dizer que o foco tem menos atrasos daquela causa do que a taxa
nacional preveria.

### 7.6 O que muda na recomendação

- **RJ: malha logística, mantida e mais precisa.** O problema não é o tempo
  típico (13 dias de SP, parecido com MG), é a cauda: pedidos que levam mais de
  2,21 vezes o típico, quase tudo em transporte. Recalibrar o prazo esconderia a
  falha: para o RJ atrasar na taxa nacional sem mudar a entrega, a promessa
  precisaria de **8 dias a mais** (de 27,0 para cerca de 35), e os pedidos da
  cauda continuariam chegando com mais de três vezes o tempo típico (42,4 dias
  em média, contra 12,7).
- **Nordeste: estimativa de prazo primeiro.** As entregas para o Nordeste não
  são irregulares para a distância; a promessa é que cobre menos da variação
  normal da rota do que no resto do país. Para o Nordeste atrasar na taxa
  nacional, a promessa precisaria de **7 dias a mais** (de 31,3 para cerca de
  38). A outra saída é encurtar o tempo típico das rotas, que é projeto de malha.
  O dataset não diz quanto venda um prazo maior custaria, então a escolha entre
  as duas fica com quem conhece a conversão.
- **Vendedor continua fora do foco** (seção 5): em nenhum dos dois focos a
  causa é despacho.

### 7.7 Limitações desta seção

- **A régua é uma escolha.** A mediana nacional define o que é "promessa
  padrão". A sensibilidade (7.5) mostra que a direção se mantém, mas a proporção
  exata muda com ela.
- **"Prazo curto" não quer dizer que o tempo típico seja aceitável.** A regra
  compara cada rota com ela mesma. Se o Nordeste deveria ser atendido mais rápido
  é outra pergunta, que pede referência externa (distância, custo de frete,
  concorrência).
- **Diagnóstico depois do fato.** O tempo típico usa a base inteira, inclusive
  pedidos posteriores a cada compra. Serve para explicar, não para prever: não
  pode virar feature do modelo de atraso.
- **Não se sabe como a Olist calcula o prazo.** A estimativa pode usar produto,
  vendedor ou época, que a régua por rota não enxerga.
- **Pedido com mais de um vendedor** em UFs diferentes (509) não tem rota e usa a
  referência da UF do cliente, assim como rotas com menos de 30 pedidos.
- **Datas impossíveis** (seção 5, 22 pedidos) entram como estão: a regra só usa
  compra, prazo estimado e entrega ao cliente.
- **Os 7 e 8 dias de 7.6** são deslocamentos uniformes da promessa para a taxa
  nacional, não uma proposta de nova estimativa por rota.

### 7.8 Queries de reprodução

Números conferidos por duas contas: o model `marts.prazo_vs_entrega` e uma query
independente sobre `obt_pedidos`, `fato_itens_pedido` e `dim_vendedores`
concordam na classificação dos 96.470 pedidos, e os excessos totais (+659 no RJ,
+537 no Nordeste) são os mesmos da seção 2.1.

```sql
-- 7.1 Folga por UF do cliente (pedidos entregues com data).
select
  cliente_uf,
  count(*)                                                       as entregues,
  round(avg(prazo_prometido_dias), 1)                            as prazo_medio,
  round(avg(tempo_entrega_dias), 1)                              as tempo_medio,
  round(avg(folga_dias), 1)                                      as folga_media,
  percentile_cont(0.5) within group (order by prazo_sobre_tipico) as prazo_sobre_tipico_mediana,
  round(100.0 * avg(case when tempo_sobre_tipico > razao_prazo_padrao then 1 else 0 end), 1) as pct_acima_padrao,
  round(100.0 * avg(case when not entregue_no_prazo then 1 else 0 end), 1) as taxa_atraso
from marts.prazo_vs_entrega
group by cliente_uf
order by taxa_atraso desc;

-- 7.2 Folga por rota (UF do vendedor > UF do cliente), rotas com 250 pedidos ou mais.
select
  rota,
  count(*)                                                       as entregues,
  round(avg(prazo_prometido_dias), 1)                            as prazo_medio,
  max(tempo_tipico_dias)                                         as tempo_tipico,
  percentile_cont(0.9) within group (order by tempo_entrega_dias) as tempo_p90,
  round(avg(prazo_prometido_dias) / max(tempo_tipico_dias), 2)   as prazo_sobre_tipico,
  round((percentile_cont(0.9) within group (order by tempo_entrega_dias)
         / max(tempo_tipico_dias))::numeric, 2)                  as p90_sobre_tipico,
  round(avg(folga_dias), 1)                                      as folga_media,
  round(100.0 * avg(case when not entregue_no_prazo then 1 else 0 end), 1) as taxa_atraso
from marts.prazo_vs_entrega
where referencia_tipico = 'rota'
group by rota
having count(*) >= 250
order by entregues desc;

-- 7.2 Escala da regua: a dispersao cresce com o tempo tipico da rota?
-- Rotas com 100 pedidos ou mais; RJ como destino fica de fora da correlacao.
with rotas as (
  select
    rota,
    right(rota, 2)                                                  as uf_destino,
    count(*)                                                        as entregues,
    max(tempo_tipico_dias)                                          as tipico,
    percentile_cont(0.9) within group (order by tempo_entrega_dias) as p90
  from marts.prazo_vs_entrega
  where referencia_tipico = 'rota'
  group by rota
  having count(*) >= 100
)
select
  count(*)                                                          as rotas,
  round(corr(tipico, p90 - tipico)::numeric, 2)                     as corr_em_dias,
  round(corr(tipico, p90 / tipico)::numeric, 2)                     as corr_em_razao,
  round(regr_slope(p90 - tipico, tipico)::numeric, 2)               as dias_extras_por_dia_tipico
from rotas
where uf_destino <> 'RJ';

-- 7.2 Mesma conta por faixa de tempo tipico, com as rotas para o RJ separadas.
with rotas as (
  select
    rota,
    right(rota, 2) = 'RJ'                                           as destino_rj,
    count(*)                                                        as entregues,
    max(tempo_tipico_dias)                                          as tipico,
    percentile_cont(0.9) within group (order by tempo_entrega_dias) as p90
  from marts.prazo_vs_entrega
  where referencia_tipico = 'rota'
  group by rota
  having count(*) >= 100
)
select
  case when tipico <= 8 then 'ate 8 dias' when tipico <= 12 then '9 a 12'
       when tipico <= 16 then '13 a 16' else '17 ou mais' end        as faixa_tipico,
  destino_rj,
  count(*)                                                          as rotas,
  sum(entregues)                                                    as entregues,
  round(avg(p90 - tipico)::numeric, 1)                              as p90_menos_tipico,
  round(avg(p90 / tipico)::numeric, 2)                              as p90_sobre_tipico
from rotas
group by 1, 2
order by 2, min(tipico);

-- 7.4 Excesso de atraso de cada foco, separado por causa.
-- Mesmo denominador da secao 2.1: todos os entregues de obt_pedidos (96.478),
-- inclusive os 8 sem data de entrega, que nao contam como atraso.
with base as (
  select o.cliente_uf, o.cliente_regiao, v.causa_atraso
  from marts.obt_pedidos o
  left join marts.prazo_vs_entrega v using (pedido_sk)
  where o.foi_entregue
),
taxa as (
  select
    avg(case when causa_atraso is not null then 1.0 else 0 end)        as t_total,
    avg(case when causa_atraso = 'prazo curto' then 1.0 else 0 end)    as t_prazo,
    avg(case when causa_atraso = 'entrega lenta' then 1.0 else 0 end)  as t_lenta
  from base
),
por_uf as (
  select
    b.cliente_uf,
    b.cliente_regiao,
    count(*)                                                         as entregues,
    count(b.causa_atraso)                                            as atrasos,
    count(*) filter (where b.causa_atraso = 'prazo curto')           as prazo_curto,
    count(*) filter (where b.causa_atraso = 'entrega lenta')         as entrega_lenta,
    count(b.causa_atraso) - count(*) * t.t_total                     as excesso,
    count(*) filter (where b.causa_atraso = 'prazo curto')   - count(*) * t.t_prazo as excesso_prazo,
    count(*) filter (where b.causa_atraso = 'entrega lenta') - count(*) * t.t_lenta as excesso_lenta
  from base b
  cross join taxa t
  group by b.cliente_uf, b.cliente_regiao, t.t_total, t.t_prazo, t.t_lenta
)
-- Excesso calculado por UF e so depois somado (secao 2.1).
select
  case when cliente_uf = 'RJ' then 'RJ'
       when cliente_regiao = 'Nordeste' then 'Nordeste' else 'demais' end as foco,
  cliente_uf,
  sum(entregues) as entregues, sum(atrasos) as atrasos,
  sum(prazo_curto) as prazo_curto, sum(entrega_lenta) as entrega_lenta,
  round(sum(excesso)) as excesso,
  round(sum(excesso_prazo)) as excesso_prazo_curto,
  round(sum(excesso_lenta)) as excesso_entrega_lenta
from por_uf
group by grouping sets ((1), (1, 2))
order by 1, excesso desc;

-- 7.5 Sensibilidade: a mesma divisao com outras reguas. Razao 1,83 e 2,73 sao
-- os quartis de prazo/tipico; 'dias +13' e a escala aditiva descartada em 7.2.
with base as (
  select
    o.cliente_uf, o.cliente_regiao,
    v.entregue_no_prazo, v.tempo_entrega_dias, v.tempo_tipico_dias
  from marts.obt_pedidos o
  left join marts.prazo_vs_entrega v using (pedido_sk)
  where o.foi_entregue
),
reguas(regua, k, dias) as (
  values ('razao 1,83', 1.83, null::numeric), ('razao 2,21', 2.21, null),
         ('razao 2,73', 2.73, null), ('dias +13', null, 13)
),
classif as (
  select
    r.regua,
    case when b.cliente_uf = 'RJ' then 'RJ'
         when b.cliente_regiao = 'Nordeste' then 'Nordeste' else 'demais' end as foco,
    case when b.entregue_no_prazo is not false then null
         when b.tempo_entrega_dias <= coalesce(b.tempo_tipico_dias * r.k,
                                               b.tempo_tipico_dias + r.dias)
              then 'prazo curto' else 'entrega lenta' end as causa
  from base b cross join reguas r
),
taxa as (
  select regua,
    avg(case when causa = 'prazo curto' then 1.0 else 0 end)   as t_prazo,
    avg(case when causa = 'entrega lenta' then 1.0 else 0 end) as t_lenta
  from classif group by regua
)
select c.regua, c.foco,
  round(count(*) filter (where causa = 'prazo curto')   - count(*) * t.t_prazo) as excesso_prazo_curto,
  round(count(*) filter (where causa = 'entrega lenta') - count(*) * t.t_lenta) as excesso_entrega_lenta
from classif c join taxa t using (regua)
where c.foco <> 'demais'
group by c.regua, c.foco, t.t_prazo, t.t_lenta
order by c.foco desc, c.regua;

-- 7.6 Quantos dias a mais de promessa cada foco precisaria para atrasar na
-- taxa nacional (6,77% dos entregues), sem mudar nada na entrega.
with base as (
  select
    case when o.cliente_uf = 'RJ' then 'RJ'
         when o.cliente_regiao = 'Nordeste' then 'Nordeste' end as foco,
    o.atraso_dias
  from marts.obt_pedidos o
  where o.foi_entregue
),
nacional as (
  select avg(case when atraso_dias > 0 then 1.0 else 0 end) as taxa from base
),
cenarios as (
  select b.foco, s.dias_a_mais,
    avg(case when b.atraso_dias > s.dias_a_mais then 1.0 else 0 end) as taxa
  from base b cross join generate_series(0, 30) s(dias_a_mais)
  where b.foco is not null
  group by b.foco, s.dias_a_mais
)
select c.foco, min(c.dias_a_mais) as dias_a_mais
from cenarios c cross join nacional n
where c.taxa <= n.taxa
group by c.foco;

-- 7.4 Vendedor contra transporte nos pedidos do RJ, por causa.
select
  coalesce(v.causa_atraso, 'no prazo')        as causa,
  count(*)                                    as pedidos,
  round(avg(f.dias_ate_transportadora), 1)    as dias_vendedor,
  round(avg(f.dias_em_transporte), 1)         as dias_transporte,
  round(avg(v.tempo_entrega_dias), 1)         as dias_total
from marts.prazo_vs_entrega v
join marts.fato_pedidos f using (pedido_sk)
where v.cliente_uf = 'RJ'
group by 1
order by 1;
```

---

## Queries de reprodução

```sql
-- Achado principal: nota por faixa de atraso
-- Atencao: NULL tratado explicitamente. Sem o primeiro WHEN, os pedidos sem
-- data de entrega caem no ELSE e contaminam a ultima faixa, porque em SQL
-- "NULL <= 0" nao e falso, e nulo.
select
  case when atraso_dias is null then 'sem data'
       when atraso_dias <= 0  then 'no prazo'
       when atraso_dias <= 7  then '1 a 7 dias'
       when atraso_dias <= 30 then '8 a 30 dias'
       else 'mais de 30' end                              as faixa,
  count(*)                                                as pedidos,
  round(avg(nota_avaliacao)::numeric, 2)                  as nota_media,
  -- Percentuais sobre os pedidos AVALIADOS, nao sobre todos.
  -- Dividir pelo total misturaria "cliente deu 1 estrela" com "cliente nao
  -- respondeu", que sao coisas diferentes. Por isso count(nota_avaliacao) no
  -- denominador, que ignora nulos, e nao count(*).
  round(100.0 * count(*) filter (where nota_avaliacao = 1)
        / nullif(count(nota_avaliacao), 0), 1)            as pct_1_estrela,
  round(100.0 * count(*) filter (where nota_avaliacao = 5)
        / nullif(count(nota_avaliacao), 0), 1)            as pct_5_estrelas
from marts.obt_pedidos
where foi_entregue
group by 1
order by 1;

-- Excesso de atraso por regiao, contra a taxa nacional.
-- ATENCAO: este recorte esconde o RJ dentro do Sudeste (ver secao 2.1).
-- Use a query por estado, logo abaixo, para decidir onde agir.
with base as (
  select avg(case when not entregue_no_prazo then 1.0 else 0 end) as taxa_nacional
  from marts.obt_pedidos where foi_entregue
)
select
  p.cliente_regiao,
  count(*)                                                     as entregues,
  sum(case when not p.entregue_no_prazo then 1 else 0 end)     as atrasos,
  round(count(*) * b.taxa_nacional)                            as esperado,
  sum(case when not p.entregue_no_prazo then 1 else 0 end)
    - round(count(*) * b.taxa_nacional)                        as excesso
from marts.obt_pedidos p
cross join base b
where p.foi_entregue
group by p.cliente_regiao, b.taxa_nacional
order by excesso desc;
-- Excesso de atraso por ESTADO: o grao certo para decidir onde agir.
-- Excesso calculado no grao mais fino e so depois agregado, para que um estado
-- grande e bom (SP) nao esconda um estado ruim (RJ) dentro da mesma regiao.
with base as (
  select avg(case when not entregue_no_prazo then 1.0 else 0 end) as taxa_nacional
  from marts.obt_pedidos where foi_entregue
)
select
  p.cliente_uf,
  p.cliente_regiao,
  count(*)                                                     as entregues,
  round(100.0 * avg(case when not p.entregue_no_prazo then 1.0 else 0 end), 1) as taxa,
  sum(case when not p.entregue_no_prazo then 1 else 0 end)
    - round(count(*) * b.taxa_nacional)                        as excesso
from marts.obt_pedidos p
cross join base b
where p.foi_entregue
group by p.cliente_uf, p.cliente_regiao, b.taxa_nacional
order by excesso desc;
```
