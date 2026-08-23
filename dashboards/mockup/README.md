# Mockup do dashboard

Referência visual da página inicial, feita antes de montar o relatório no
Looker Studio. Abra `olist_visao_geral.html` no navegador.

## O que isto é, e o que não é

**É** um mockup: os números estão fixos no código, copiados das marts em
23/08/2026. Serve para decidir layout, hierarquia visual e quais métricas
merecem destaque, sem gastar tempo arrastando campo no Looker.

**Não é** um dashboard. Não lê o banco, não atualiza, não filtra de verdade
(os controles são decorativos). O relatório real lê `marts.obt_pedidos` e
`marts.obt_itens` no Neon, ao vivo. Veja o passo a passo em
[../README.md](../README.md).

## Base dos números

Tudo na mesma janela: **01/01/2017 a 31/08/2018, todos os status de pedido.**

| Métrica | Valor |
|---|---|
| Receita total | R$ 15.786.204 |
| Pedidos | 99.092 |
| Ticket médio | R$ 159,31 |
| Nota média | 4,09 |
| Entregue no prazo | 93,2% (base: 96.211 entregues) |

Note que estes valores são da **janela filtrada** e por isso diferem da tabela
de conferência do [../README.md](../README.md), que cobre o dataset inteiro
(99.441 pedidos, R$ 15.843.553). A diferença são 349 pedidos nas pontas da
série. As duas tabelas estão certas; o que muda é o filtro.

## Duas decisões que valem explicar numa entrevista

**Por que a janela começa em jan/2017.** O dataset cobre set/2016 a out/2018,
mas as pontas são resíduo de coleta: set/2016 tem 4 pedidos, dez/2016 tem 1, e
set-out/2018 somam 20. São 0,35% do total. Plotar o período inteiro achata a
série contra o eixo e desenha uma queda final que não é queda de vendas, é fim
de dataset. Cortar as pontas é decisão de análise, e precisa estar escrita.

**Por que "entregue no prazo" tem outra base.** É o único indicador calculado
sobre um subconjunto (só os pedidos entregues). Os 2.881 pedidos em trânsito ou
cancelados não têm prazo vencido, então contá-los como atraso derrubaria o
número para 90,4% sem que nada de real tivesse acontecido. O card diz a base no
subtítulo, justamente para ninguém precisar adivinhar.

## Histórico

A primeira versão saiu de um prompt para o Gemini e tinha três defeitos, todos
corrigidos aqui:

1. **Dados inventados.** Das 9 UFs do mapa, 6 estavam erradas: RS, PR, BA, DF e
   PE inflados em cerca de 25%, e PA subestimado. Pior, PE e PA nem estão no
   top 9 (quem está é SC e GO). O modelo acertou só os três estados que o prompt
   entregou explicitamente e preencheu o resto com valores plausíveis.
2. **Filtros incoerentes.** O controle dizia "Status: Entregue" enquanto os
   scorecards mostravam o total de todos os status.
3. **Encoding quebrado.** O arquivo foi salvo em codificação errada e todo
   texto acentuado virou mojibake.

Vale guardar o item 1 como lembrete para a Fase 6: modelo de linguagem preenche
lacuna com o que parece razoável em vez de admitir que não sabe. O agente de IA
sobre as marts vai precisar de guarda contra exatamente isso.

## Dependências

O arquivo carrega Chart.js e Leaflet por CDN, e os tiles do mapa vêm do CARTO.
Precisa de internet para renderizar. Se um dia for hospedado em algum lugar com
bloqueio de origem externa, essas três dependências precisam ser embutidas.
