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

O problema real está no **Nordeste**, que sozinho responde por **537 dos 569
atrasos em excesso** do país.

**Recomendação.** Priorizar a operação logística do Nordeste. Trazer a região
para a média nacional eliminaria cerca de 537 atrasos por ano, associados a
**R$ 112 mil** em receita, e evitaria a queda de 2,6 pontos de nota nesses
pedidos. Nenhuma outra região apresenta atraso em excesso relevante.

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

O Nordeste responde por **94% de todo o atraso em excesso do país**. Sudeste,
Sul e Centro-Oeste operam abaixo da média: não há problema a corrigir neles.

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

## 5. Limitações e próximo passo

**O que esta análise ainda não responde: de quem é o atraso.** O tempo entre a
compra e a entrega tem duas partes: o tempo que o vendedor leva para despachar, e
o tempo que a transportadora leva para entregar. A recomendação muda
completamente conforme a resposta. Se o gargalo é o vendedor, a ação é
onboarding e SLA de despacho. Se é a transportadora, a ação é malha logística.

Os campos existem no staging (`approved_at`, `delivered_carrier_at`) mas ainda
não foram promovidos ao `fato_pedidos`. Promover esses dois campos e decompor o
tempo de entrega é o próximo passo desta análise, e é um caso em que a pergunta
de negócio dirige a mudança de modelagem, não o contrário.

**Outras limitações:**

- Dataset histórico e fechado (2016 a 2018). Não há como validar se as conclusões
  se sustentam hoje.
- A associação entre atraso e nota é forte e robusta a região, mas não é prova
  causal. Vendedor, categoria e distância continuam como confundidores possíveis.
- 278 CEPs de cliente não existem na base de geolocalização, o que limita
  análises de distância.

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

-- Excesso de atraso por regiao, contra a taxa nacional
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
```
