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

> Os três confundidores dessa ressalva foram testados nas seções 1.1 e 1.2. O
> resultado: juntos, explicam menos de 3% da queda.

### 1.1 Distância vendedor para cliente: o buraco da geolocalização

Controlar por distância exige a distância de todo pedido, e a base de
geolocalização do Olist não cobre todos os CEPs.

**O tamanho do buraco.** As limitações falavam em "278 CEPs". São **157 CEPs de
cliente, que somam 278 pedidos**: o teste em aviso do `_marts.yml` conta
pedidos, não CEPs. Mais um pedido perde a coordenada porque todos os pontos do
CEP dele (83252, no Paraná) caem fora do país, o que dá 279. Do lado do
vendedor, 7 vendedores não estão na base e são o vendedor principal de 217
pedidos.

| Sem coordenada | Pedidos | % dos pedidos | Receita | % da receita |
|---|---|---|---|---|
| Cliente | 279 | 0,28% | R$ 44.613 | 0,28% |
| Vendedor | 217 | 0,22% | R$ 31.135 | 0,20% |
| **Pelo menos um dos dois** | **491** | **0,49%** | **R$ 75.590** | **0,48%** |

Receita aqui é a mesma conta do resumo (itens mais frete, todos os 99.441
pedidos, set/2016 a out/2018, total de R$ 15,8 milhões). O buraco é pequeno
demais para mudar uma conclusão sozinho, mas um join que descartasse esses
pedidos tiraria da análise justamente os CEPs novos ou raros, sem aviso.

**O fallback testado.** Dois candidatos: o centroide do município (média dos
CEPs da mesma cidade e UF) e o do prefixo de 3 dígitos do CEP. Para escolher,
a mesma pergunta para os dois: apagando um CEP conhecido e estimando pelo resto,
quanto se erra? O teste roda sobre os 99.162 pedidos cujo CEP de cliente tem
coordenada.

| Fallback | Recupera (dos 279) | Pedidos no teste | Erro mediano | Erro p90 |
|---|---|---|---|---|
| Município | 220 | 79.854 | 4,7 km | 16,2 km |
| Prefixo de 3 dígitos | 276 | 98.722 | 4,2 km | 43,2 km |
| **Município, e sem ele o prefixo** | **279** | | | |

O município vem primeiro: o erro mediano é parecido, mas a cauda do prefixo é
quase três vezes maior, porque no interior três dígitos cobrem várias cidades.
Ressalva: o teste do município só existe onde ele tem mais de um CEP, ou seja,
em cidades maiores; o erro em cidade pequena não está medido. Para escala, a
distância mediana entre vendedor e cliente é de 435 km, então um erro de 5 a
40 km raramente troca o pedido de faixa. Os 7 vendedores se resolvem todos pelo
município.

**O que ficou na mart.** `marts.distancia_pedido`, uma linha por pedido:

| Método | Pedidos |
|---|---|
| Os dois pontos pelo próprio CEP | 98.175 |
| Pelo menos um ponto por fallback | 491 |
| Sem distância (pedido sem item, logo sem vendedor) | 775 |

Cobertura de **100% dos pedidos com vendedor**. Método: haversine (linha reta,
não estrada); vendedor do item de maior valor, a mesma regra do modelo de
previsão (98% dos pedidos têm vendedor único); ponto fora da caixa do Brasil
descartado um a um, antes da média do CEP. As colunas `metodo_geo_cliente` e
`metodo_geo_vendedor` dizem de onde veio cada ponto, e `distancia_por_cep`
separa quem precisa da distância exata. Testes no dbt: chave única ligada ao
`fato_pedidos`, valores aceitos, distância entre 0 e 4.500 km e um teste de
cobertura que falha se um pedido com vendedor ficar sem distância, ou se nenhum
pedido tiver vendedor (para não passar com zero casos).

O modelo de previsão continua calculando a própria distância, sem o fallback.
Usar a mart como feature fica para depois.

### 1.2 O efeito sobrevive a categoria, distância e vendedor

A mesma tabela da região, refeita por grupo de categoria (os 14 grupos das
macros, mais "Sem categoria") e por faixa de distância. Categoria e vendedor são
os do item de maior valor do pedido. "Pedidos" são os entregues e avaliados;
"Atrasados" são os avaliados com 1 a 30 dias de atraso, para mostrar quando uma
célula é pequena demais para ler.

| Categoria | Pedidos | Atrasados | No prazo | 1 a 7 dias | 8 a 30 dias | Queda até 1 a 7 | Queda até 8 a 30 |
|---|---|---|---|---|---|---|---|
| Casa e Decoração | 22.314 | 1.418 | 4,21 | 2,71 | 1,65 | 1,50 | 2,56 |
| Eletrônicos e Informática | 14.886 | 967 | 4,22 | 2,80 | 1,62 | 1,42 | 2,59 |
| Beleza e Saúde | 11.651 | 790 | 4,39 | 2,78 | 1,68 | 1,61 | 2,71 |
| Moda e Acessórios | 8.763 | 548 | 4,31 | 2,60 | 1,66 | 1,71 | 2,65 |
| Esporte e Lazer | 7.448 | 460 | 4,38 | 2,60 | 1,66 | 1,78 | 2,72 |
| Bebês e Brinquedos | 6.495 | 424 | 4,35 | 2,48 | 1,61 | 1,87 | 2,73 |
| Ferramentas e Construção | 5.365 | 327 | 4,30 | 2,76 | 1,83 | 1,55 | 2,47 |
| Automotivo | 3.776 | 254 | 4,29 | 2,81 | 1,52 | 1,49 | 2,77 |
| Diversos | 3.766 | 200 | 4,34 | 2,71 | 1,58 | 1,63 | 2,76 |
| Escritório e Papelaria | 3.475 | 226 | 4,20 | 2,81 | 1,66 | 1,39 | 2,54 |
| Eletrodomésticos | 1.813 | 79 | 4,30 | 2,80 | 1,52 | 1,50 | 2,79 |
| Livros, Mídia e Arte | 1.710 | 118 | 4,49 | 2,84 | 1,69 | 1,65 | 2,80 |
| Pet Shop | 1.673 | 83 | 4,38 | 2,65 | 1,68 | 1,73 | 2,70 |
| Sem categoria | 1.352 | 92 | 4,19 | 2,50 | 1,58 | 1,69 | 2,61 |
| Alimentos e Bebidas | 931 | 45 | 4,45 | 2,81 | 1,67 | 1,65 | 2,79 |
| Indústria e Serviços | 406 | 21 | 4,28 | 3,14 | 1,14 | 1,14 | 3,14 |

| Distância | Pedidos | Atrasados | No prazo | 1 a 7 dias | 8 a 30 dias | Queda até 1 a 7 | Queda até 8 a 30 |
|---|---|---|---|---|---|---|---|
| Até 100 km | 17.826 | 760 | 4,34 | 2,98 | 1,84 | 1,36 | 2,50 |
| 100 a 500 km | 36.882 | 2.107 | 4,31 | 2,69 | 1,62 | 1,61 | 2,69 |
| 500 a 1.000 km | 25.819 | 1.715 | 4,26 | 2,61 | 1,65 | 1,65 | 2,61 |
| 1.000 a 2.000 km | 9.718 | 854 | 4,24 | 2,73 | 1,75 | 1,51 | 2,49 |
| Acima de 2.000 km | 5.579 | 616 | 4,24 | 2,61 | 1,48 | 1,62 | 2,76 |

A queda até 8 a 30 dias fica entre 2,47 e 2,80 em 14 dos 15 grupos de
categoria e entre 2,49 e 2,76 nas cinco faixas de distância, perto do intervalo
das regiões (2,55 a 2,74). A exceção, Indústria e Serviços, tem 21 pedidos
atrasados e não sustenta leitura. A queda até 1 a 7 dias varia mais (1,36 a
1,87), e a menor é a das entregas até 100 km; não investiguei por quê.

**Um modelo com tudo junto.** Tabela por fator controla um fator de cada vez.
Para controlar todos ao mesmo tempo, uma regressão linear da nota (1 a 5) sobre
a faixa de atraso, com região do cliente, grupo de categoria e faixa de
distância como controles. A última linha acrescenta efeito fixo de vendedor:
compara só pedidos do mesmo vendedor, o que tira da conta tudo que é fixo nele
(qualidade do produto, embalagem, cidade de origem). Erro-padrão agrupado por
vendedor, porque pedidos do mesmo vendedor não são independentes. Base: 95.824
pedidos entregues e avaliados, 2.952 vendedores.

| Especificação | 1 a 7 dias | IC 95% | 8 a 30 dias | IC 95% | Acima de 30 | IC 95% |
|---|---|---|---|---|---|---|
| Só atraso | -1,58 | [-1,63; -1,52] | -2,64 | [-2,69; -2,59] | -2,23 | [-2,41; -2,06] |
| + região | -1,57 | [-1,63; -1,51] | -2,63 | [-2,68; -2,58] | -2,22 | [-2,40; -2,05] |
| + região, categoria e distância | -1,57 | [-1,63; -1,51] | -2,62 | [-2,68; -2,57] | -2,21 | [-2,38; -2,03] |
| **+ efeito fixo de vendedor** | **-1,53** | **[-1,60; -1,47]** | **-2,58** | **[-2,63; -2,52]** | **-2,17** | **[-2,35; -1,99]** |

Os coeficientes são pontos de nota em relação a um pedido no prazo. A primeira
linha é a queda bruta (-1,575; a diferença entre as médias já arredondadas,
4,29 e 2,72, dá 1,57). Com todos os
controles e comparando dentro do mesmo vendedor, a queda de 1 a 7 dias vai a
**1,53 ponto, com intervalo de confiança de 95% entre 1,47 e 1,60**: os
controles explicam 2,6% dela. Os controles em si mexem pouco na nota: a maior
diferença de categoria é +0,26 (Livros, Mídia e Arte contra Casa e Decoração),
a maior entre faixas de distância é de 0,10 e a maior entre regiões, de 0,09. Restringindo aos 95.347 pedidos com distância pelo próprio CEP, sem
fallback, o resultado é o mesmo (-1,53, IC de -1,59 a -1,47).

**O que isso muda e o que não muda na conclusão.**

- **Muda:** categoria, distância e vendedor deixam de ser confundidores
  plausíveis. A queda não é composição de nenhum deles, nem de todos juntos.
- **Não muda:** continua sendo associação ajustada pelo que o dataset mede, não
  prova de causa. Ficam de fora o que gera atraso e insatisfação ao mesmo tempo
  (extravio, item errado, reenvio), o prazo prometido, a expectativa do cliente e
  o produto específico dentro do vendedor. E o modelo trata a nota de 1 a 5 como
  número: o coeficiente é diferença de médias, não probabilidade de nota baixa.
- **A frase do resumo:** "o atraso derruba a nota de 4,29 para 2,72" continua
  correta como descrição. Como estimativa controlada, a queda de 1 a 7 dias de
  atraso é de 1,53 ponto (IC 95% de 1,47 a 1,60).

Reprodução: `python -m scripts.controle_atraso`, da raiz, depois do `dbt
build`. As funções do estimador têm testes de resposta conhecida em
`tests/test_controle_atraso.py`.

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
- A associação entre atraso e nota resiste a região, categoria, distância e
  vendedor (seção 1.2): com tudo controlado, a queda de 1 a 7 dias é de 1,53
  ponto (IC 95% de 1,47 a 1,60), contra 1,57 sem controle. Continua não sendo
  prova causal: problema no pedido que gera atraso e insatisfação ao mesmo
  tempo, prazo prometido e expectativa do cliente não estão controlados.
- 157 CEPs de cliente (278 pedidos, não "278 CEPs" como dizia uma versão
  anterior) e 7 de vendedor não existem na base de geolocalização. A distância
  desses 491 pedidos (0,48% da receita) vem do centroide do município ou do
  prefixo de 3 dígitos, com erro mediano estimado de 4 a 5 km (seção 1.1). Quem
  precisar da distância exata filtra `distancia_por_cep`.

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

-- Secao 1.1: cobertura da distancia por metodo (marts.distancia_pedido).
select metodo_geo_cliente, metodo_geo_vendedor, count(*) as pedidos,
       count(distancia_km) as com_distancia
from marts.distancia_pedido
group by 1, 2
order by 3 desc;

-- Secao 1.1: pedidos e receita que dependem do fallback.
select
  count(*) filter (where d.metodo_geo_cliente <> 'cep')          as pedidos_cliente,
  sum(f.valor_total) filter (where d.metodo_geo_cliente <> 'cep') as receita_cliente,
  count(*) filter (where not d.distancia_por_cep and d.distancia_km is not null)          as pedidos_fallback,
  sum(f.valor_total) filter (where not d.distancia_por_cep and d.distancia_km is not null) as receita_fallback,
  sum(f.valor_total)                                              as receita_total
from marts.distancia_pedido d
join marts.fato_pedidos f using (pedido_sk);

-- Secao 1.1: erro do fallback, deixando um CEP conhecido de fora.
-- Para cada pedido com CEP conhecido, estima o ponto pela media dos OUTROS
-- CEPs do municipio (ou do prefixo de 3 digitos) e mede a distancia ao real.
with pontos as (
  select * from staging.stg_olist__geolocation_pontos
  where latitude between -33.8 and 5.3 and longitude between -74.0 and -34.7
), por_cep as (
  select zip_code_prefix, avg(latitude) as lat, avg(longitude) as lng,
         mode() within group (order by cidade_chave) as cidade_chave,
         mode() within group (order by state)        as uf
  from pontos group by 1
), mun as (
  select cidade_chave, uf, sum(lat) as slat, sum(lng) as slng, count(*) as n from por_cep group by 1, 2
), p3 as (
  select zip_code_prefix / 100 as p, sum(lat) as slat, sum(lng) as slng, count(*) as n from por_cep group by 1
), estimado as (
  select c.lat, c.lng,
    (m.slat - c.lat) / nullif(m.n - 1, 0) as mlat, (m.slng - c.lng) / nullif(m.n - 1, 0) as mlng,
    (p.slat - c.lat) / nullif(p.n - 1, 0) as plat, (p.slng - c.lng) / nullif(p.n - 1, 0) as plng
  from staging.stg_olist__customers cli
  join por_cep c on c.zip_code_prefix = cli.zip_code_prefix
  -- mesma chave da macro chave_municipio
  left join mun m on m.uf = cli.state and m.cidade_chave = regexp_replace(
      translate(lower(trim(cli.city)), 'áàâãäéèêëíìîïóòôõöúùûüç''-', 'aaaaaeeeeiiiiooooouuuuc  '),
      '\s+', ' ', 'g')
  left join p3 p on p.p = cli.zip_code_prefix / 100
), erro as (
  select
    case when mlat is not null then 2 * 6371 * asin(least(1.0, sqrt(power(sin(radians(mlat - lat) / 2), 2)
      + cos(radians(lat)) * cos(radians(mlat)) * power(sin(radians(mlng - lng) / 2), 2)))) end as km_municipio,
    case when plat is not null then 2 * 6371 * asin(least(1.0, sqrt(power(sin(radians(plat - lat) / 2), 2)
      + cos(radians(lat)) * cos(radians(plat)) * power(sin(radians(plng - lng) / 2), 2)))) end as km_prefixo_3
  from estimado
)
select
  count(km_municipio)                                          as pedidos_municipio,
  percentile_cont(0.5) within group (order by km_municipio)    as mediana_municipio,
  percentile_cont(0.9) within group (order by km_municipio)    as p90_municipio,
  count(km_prefixo_3)                                          as pedidos_prefixo_3,
  percentile_cont(0.5) within group (order by km_prefixo_3)    as mediana_prefixo_3,
  percentile_cont(0.9) within group (order by km_prefixo_3)    as p90_prefixo_3
from erro;
```

As tabelas por categoria e por distância e a regressão da seção 1.2 saem de
`python -m scripts.controle_atraso`, que imprime também a tabela por região
para conferência contra a seção 1.
