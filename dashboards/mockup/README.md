# Mockup do dashboard executivo

Referencia visual da pagina inicial ("Visao Geral Comercial"), feita como blueprint antes de montar o relatorio no Looker Studio.

Abra `olist_visao_geral.html` no navegador (basta dar dois cliques no arquivo ou arrastar para o Chrome/Edge).

---

## O que foi melhorado nesta versao

1. **Design Executivo Moderno:** Layout estruturado no formato widescreen 16:9 (1600 x 900 px no Looker Studio), com cards em estilo glassmorphism/elevado, micro-sombras e tipografia profissional (*Plus Jakarta Sans* e *Inter*).
2. **Alternancia de Tema (Claro / Escuro):** Botao no topo para alternar instantaneamente entre Modo Claro (estilo corporativo clean) e Modo Escuro (estilo tech/SaaS), adaptando mapa e graficos. Ideal para escolher qual tema aplicar no Looker Studio.
3. **Painel Lateral "Blueprint Looker Studio":** Gaveta retratil interativa no proprio mockup com:
   - Medidas de pagina (1600 x 900 px, 16:9) e padding.
   - Codigos hexadecimais da paleta de cores para copiar e colar no Looker Studio.
   - Tabela de mapeamento 1-para-1 de cada grafico (tipo de componente no Looker, campos de dimensao, metrica e agregacao).
   - Lembretes criticos de configuracao (upload do certificado SSL `isrgrootx1.pem` no conector Postgres do Neon e regra do filtro de pedidos entregues).
4. **Scorecards com Indicadores de Contexto:** Icones vetoriais dedicados, valores em destaque com tipografia tabular, micro-badges com fatos medidos (crescimento jan-ago a/a, frete sobre a receita, taxa de atraso, CSAT) e barra de progresso no card de entrega no prazo. Nenhum badge usa meta, porque o projeto nao tem meta definida.
5. **Graficos com Gradientes e Anotacao:** 
   - Serie temporal com area sombreada suave e destaque especial anotado para o pico da Black Friday em nov/2017 (R$ 1,18 mi).
   - Grafico de barras horizontais arredondadas para receita regional com percentuais em tooltip.
   - Top 5 categorias com nomes formatados e legiveis.
   - Distribuicao das notas colorida do vermelho ao verde esmeralda evidenciando a curva em J.
   - Mapa geografico interativo com bolhas proporcionais a receita das 9 principais UFs e mini-ranking flutuante.
6. **Simulacao de Filtros:** Selecao interativa no controle de regiao para demonstrar como o painel responde aos filtros do usuario.

---

## Base dos numeros

Tudo na mesma janela analitica: **01/01/2017 a 31/08/2018, todos os status de pedido.**

| Metrica | Valor | Fonte / Grao |
|---|---|---|
| Receita total | R$ 15.786.204 (R$ 15,79 mi) | `marts.obt_pedidos` (itens + frete) |
| Pedidos | 99.092 | `marts.obt_pedidos` (todos os status) |
| Ticket medio | R$ 159,31 | `marts.obt_pedidos` (por pedido) |
| Entregue no prazo | 93,2% | `marts.obt_pedidos` (base: 96.211 entregues) |
| Nota media | 4,09 / 5,0 | `marts.obt_pedidos` (pedidos avaliados) |
| CSAT (notas 4 e 5) | 77,1% | `marts.obt_pedidos` (pedidos avaliados) |
| Receita jan-ago/2018 contra jan-ago/2017 | +139% | `marts.obt_pedidos` |
| Frete sobre a receita | 14,2% | `marts.obt_pedidos` |

Valores da **janela filtrada**, diferindo dos 99.441 pedidos e R$ 15.843.553 do dataset total por 349 pedidos nas pontas residuais (set/2016 e set-out/2018).

---

## Regras de negocio essenciais para a implementacao no Looker Studio

1. **Por que a janela comeca em jan/2017:**
   O dataset cobre set/2016 a out/2018, mas as pontas sao residuo de coleta (set/2016 tem 4 pedidos, dez/2016 tem 1, e set-out/2018 somam 20 pedidos). Juntas sao apenas 0,35% do total. Plotar o periodo bruto inteiro achata a serie temporal contra o eixo e desenha uma falsa queda nas pontas.
2. **Cuidado com o denominador de "Entregue no prazo":**
   E o unico indicador calculado apenas sobre os pedidos com status `delivered` (96.211 pedidos). Os 2.881 pedidos em transito ou cancelados nao tem prazo vencido. Se incluidos no denominador, derrubam o indicador para 90,4% de forma incorreta. No Looker Studio, aplique sempre o filtro de componente `foi_entregue = true` nesse scorecard.
3. **Nunca misturar graos no mesmo grafico:**
   Metricas de receita global, frete, pedidos e clientes vem de `obt_pedidos`. Metricas de produtos, categorias e vendedores vem de `obt_itens`.
