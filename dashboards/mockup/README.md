# Mockup do dashboard executivo

Referência visual da página inicial ("Visão Geral Comercial"), feita como blueprint antes de montar o relatório no Looker Studio.

Abra `olist_visao_geral.html` no navegador (basta dar dois cliques no arquivo ou arrastar para o Chrome/Edge).

---

## O que foi melhorado nesta versão

1. **Design Executivo Moderno:** Layout estruturado no formato widescreen 16:9 (1600 x 900 px no Looker Studio), com cards em estilo glassmorphism/elevado, micro-sombras e tipografia profissional (*Plus Jakarta Sans* e *Inter*).
2. **Alternância de Tema (Claro / Escuro):** Botão no topo para alternar instantaneamente entre Modo Claro (estilo corporativo clean) e Modo Escuro (estilo tech/SaaS), adaptando mapa e gráficos. Ideal para escolher qual tema aplicar no Looker Studio.
3. **Painel Lateral "Blueprint Looker Studio":** Gaveta retrátil interativa no próprio mockup com:
   - Medidas de página (1600 x 900 px, 16:9) e padding.
   - Códigos hexadecimais da paleta de cores para copiar e colar no Looker Studio.
   - Tabela de mapeamento 1-para-1 de cada gráfico (tipo de componente no Looker, campos de dimensão, métrica e agregação).
   - Lembretes críticos de configuração (upload do certificado SSL `isrgrootx1.pem` no conector Postgres do Neon e regra do filtro de pedidos entregues).
4. **Scorecards com Indicadores de Contexto:** Ícones vetoriais dedicados, valores em destaque com tipografia tabular, micro-badges com fatos medidos (crescimento jan-ago a/a, frete sobre a receita, taxa de atraso, CSAT) e barra de progresso no card de entrega no prazo. Nenhum badge usa meta, porque o projeto não tem meta definida.
5. **Gráficos com Gradientes e Anotação:** 
   - Série temporal com área sombreada suave e destaque especial anotado para o pico da Black Friday em nov/2017 (R$ 1,18 mi).
   - Gráfico de barras horizontais arredondadas para receita regional com percentuais em tooltip.
   - Top 5 categorias com nomes formatados e legíveis.
   - Distribuição das notas colorida do vermelho ao verde esmeralda evidenciando a curva em J.
   - Mapa geográfico interativo com bolhas proporcionais à receita das 9 principais UFs e mini-ranking flutuante.
6. **Simulação de Filtros:** Seleção interativa no controle de região para demonstrar como o painel responde aos filtros do usuário.

---

## Base dos números

Tudo na mesma janela analítica: **01/01/2017 a 31/08/2018, todos os status de pedido.**

| Métrica | Valor | Fonte / Grão |
|---|---|---|
| Receita total | R$ 15.786.204 (R$ 15,79 mi) | `marts.obt_pedidos` (itens + frete) |
| Pedidos | 99.092 | `marts.obt_pedidos` (todos os status) |
| Ticket médio | R$ 159,31 | `marts.obt_pedidos` (por pedido) |
| Entregue no prazo | 93,2% | `marts.obt_pedidos` (base: 96.211 entregues) |
| Nota média | 4,09 / 5,0 | `marts.obt_pedidos` (pedidos avaliados) |
| CSAT (notas 4 e 5) | 77,1% | `marts.obt_pedidos` (pedidos avaliados) |
| Receita jan-ago/2018 contra jan-ago/2017 | +139% | `marts.obt_pedidos` |
| Frete sobre a receita | 14,2% | `marts.obt_pedidos` |

Valores da **janela filtrada**, diferindo dos 99.441 pedidos e R$ 15.843.553 do dataset total por 349 pedidos nas pontas residuais (set/2016 e set-out/2018).

---

## Regras de negócio essenciais para a implementação no Looker Studio

1. **Por que a janela começa em jan/2017:**
   O dataset cobre set/2016 a out/2018, mas as pontas são resíduo de coleta (set/2016 tem 4 pedidos, dez/2016 tem 1, e set-out/2018 somam 20 pedidos). Juntas são apenas 0,35% do total. Plotar o período bruto inteiro achata a série temporal contra o eixo e desenha uma falsa queda nas pontas.
2. **Cuidado com o denominador de "Entregue no prazo":**
   É o único indicador calculado apenas sobre os pedidos com status `delivered` (96.211 pedidos). Os 2.881 pedidos em trânsito ou cancelados não têm prazo vencido. Se incluídos no denominador, derrubam o indicador para 90,4% de forma incorreta. No Looker Studio, aplique sempre o filtro de componente `foi_entregue = true` nesse scorecard.
3. **Nunca misturar grãos no mesmo gráfico:**
   Métricas de receita global, frete, pedidos e clientes vêm de `obt_pedidos`. Métricas de produtos, categorias e vendedores vêm de `obt_itens`.

---

## Onde o relatório real divergiu do mockup

O mockup foi o ponto de partida, não a especificação final. Na montagem, cinco
decisões mudaram, todas por motivo de dado:

| No mockup | No relatório | Por quê |
|---|---|---|
| Card de ticket médio | Card de clientes únicos | Escolha do dono |
| Badges de variação nos cards | Sem variação | "Período anterior" de uma janela de 20 meses compara com 329 pedidos e daria +27.506% |
| Receita por região | **Taxa de atraso por região** com linha da média | Receita por região repetia o mapa; a taxa conta o achado do projeto |
| Notas do vermelho ao verde | Cinza para 1 a 3, azul para 4 e 5 | Semáforo destoava da página; o azul destaca os satisfeitos, que é a definição do CSAT |
| Mapa de bolhas | Mapa preenchido por estado | Bolhas por CEP seriam 19 mil pontos |

A configuração real de cada componente está em [../README.md](../README.md).
