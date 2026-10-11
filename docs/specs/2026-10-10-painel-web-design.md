# Etapa 7: painel web com o agente junto (desenho)

**Data:** 10/10/2026. **Status:** desenho aprovado em conversa; aguardando revisão
desta especificação.

## Por que

O Power BI da Etapa 5 não é publicado: publicar exige conta de trabalho ou de
escola, e a conta de trabalho do dono não é usada neste projeto. Quem visita o
portfólio só vê prints. O agente da Etapa 6 está num link público, separado.

O dono quer um BI mais bonito, com HTML e CSS, e o agente no mesmo lugar, para
quem visita abrir **um link só**. Referências trazidas por ele: um painel escuro
com cartões coloridos e brilho, um vídeo com um assistente "Tire sua dúvida" ao
lado do painel, e um vídeo com um relatório inteiro feito em HTML dentro do
Power BI.

Decisões do dono nesta conversa:

1. **Os dois, em etapas:** primeiro o painel web com o agente (Etapa 7, esta
   especificação); depois o HTML dentro do Power BI (Etapa 8, desenho próprio).
2. **Conteúdo:** as 3 páginas do Power BI (Visão executiva, Entrega e risco,
   Vendedores), com os mesmos números.
3. **Agente:** painel lateral "Tire sua dúvida" em cada página, sabendo a página
   e os filtros, e a página "Pergunte aos dados" para conversa longa.
4. **Abordagem:** o mesmo app Streamlit, não um site estático à parte.
5. **Visual:** escolha delegada. Escolhido: escuro como padrão no estilo da
   referência, com o verde menta do agente como cor principal e azul, violeta e
   âmbar de apoio nos cartões; tema claro no botão de sol/lua.

**Critério de sucesso:** um visitante abre https://painel-olist.streamlit.app/,
vê as 3 páginas do painel com os mesmos números do Power BI (conferidos por
teste), troca período e região, e pergunta ao agente sem sair da página.

## Fora do escopo

- HTML dentro do Power BI (Etapa 8).
- Mapa do Brasil, exportação de dados, drill-through.
- Segurança por usuário (RLS): o app é público e os dados também. O RLS segue
  demonstrado no Power BI.
- Login, contas, persistência de conversa entre sessões.

## Arquitetura

O ponto de entrada continua `agente/app.py`, para o link e a configuração do
Streamlit Cloud não mudarem. Ele passa a ser um roteador (`st.navigation`) com 4
páginas:

| Página | Arquivo | Conteúdo |
|---|---|---|
| Visão executiva (padrão) | `painel/paginas/executivo.py` | Filtros período e região; 5 cartões (Receita, Pedidos, Ticket médio, % no prazo, Nota média) com destaque do último mês contra o anterior; receita por mês e no mesmo mês do ano anterior; placar mensal |
| Entrega e risco | `painel/paginas/entrega.py` | Filtro período; 3 cartões (Taxa de atraso com destaque, Pedidos em alerta, Receita em risco); taxa de atraso por região contra a nacional; atraso em excesso por UF (barras divergentes); pedidos em andamento por probabilidade de atraso |
| Vendedores | `painel/paginas/vendedores.py` | Filtro período; 3 cartões (Receita de itens com destaque, Itens, Taxa de atraso dos itens); receita de itens por grupo de categoria; receita e atraso por vendedor |
| Pergunte aos dados | `painel/paginas/pergunte.py` | O chat atual do agente, em página inteira |

Pacote novo `painel/`, separado de `agente/`:

| Módulo | Responsabilidade |
|---|---|
| `painel/filtros.py` | `Filtros(inicio: date, fim: date, regiao: str \| None)`; padrão 01/01/2017 a 31/08/2018 e região "Todas"; mês de referência = último mês do período; texto do contexto para o agente |
| `painel/consultas.py` | Uma função por visual, `(conexao, filtros) -> pandas.DataFrame`, SQL parametrizado (`%s`, nunca texto do usuário concatenado) sobre as marts |
| `painel/metricas.py` | Definições compartilhadas em SQL (receita, pedidos, ticket, % no prazo, nota, taxa de atraso, atraso em excesso, receita em risco, variação mensal em % e em pontos percentuais) |
| `painel/cartoes.py` | HTML dos cartões de indicador (ícone, valor, destaque com seta), com escape |
| `painel/graficos.py` | Gráficos Altair no tema: área com degradê, barras horizontais, barras divergentes |
| `painel/lateral.py` | Painel "Tire sua dúvida": coluna à direita com o chat compacto |

O que já existe e é reaproveitado: `agente/banco.py` (conexão e transação só de
leitura), `agente/tema.py` (paletas e CSS, ampliado para cartões e páginas),
`agente/apresentacao.py` (formatos pt-BR, tabela HTML), `agente/agente.py`.

### Dados

- Mesma conexão do agente: usuário `agente_leitura` no Neon, transação somente
  leitura e tempo máximo. As tabelas usadas pelo painel (`fato_pedidos`,
  `fato_itens_pedido`, `dim_clientes`, `dim_produtos`, `dim_vendedores`,
  `dim_tempo`, `previsao_atraso`) já têm `SELECT` para esse usuário.
- O painel roda SQL escrito por nós, não pelo modelo; por isso não passa pela
  guarda do agente, mas usa `banco.executar` (read-only, timeout).
- Cache: `st.cache_data(ttl=3600)` por (função, filtros). As marts só mudam numa
  republicação; uma hora de atraso é aceitável.
- Definições idênticas às medidas DAX da Etapa 5 (ver
  `dashboards/powerbi/Olist.SemanticModel`), incluindo: % no prazo e taxa de
  atraso só sobre pedidos com `entregue_no_prazo` não nulo; atraso em excesso
  por UF = atrasos da UF menos entregues da UF vezes a taxa nacional (taxa sem
  filtro de cliente, medida `Atraso em Excesso`); pedidos em alerta e receita em
  risco sobre `previsao_atraso` com `alerta` e `conjunto in ('teste',
  'em_andamento')`, como as medidas do Power BI; a tabela de risco lista só
  `conjunto = 'em_andamento'`; destaques do último mês do período contra o
  anterior, em % para valores e em pontos percentuais para taxas.

### Filtros

- **Período** (todas as páginas) por `st.date_input` de intervalo, limitado a
  set/2016 a out/2018.
- **Região do cliente** (só Visão executiva, como no Power BI): Todas, Norte,
  Nordeste, Centro-Oeste, Sudeste, Sul.
- Os filtros ficam no `session_state` e na URL (`?inicio=2017-01-01&fim=...`),
  como o tema, para um link reproduzir a mesma visão.

### Agente junto do painel

- Botão "Tire sua dúvida" no topo de cada página do painel abre uma coluna à
  direita (layout em 2 colunas, painel à esquerda); o botão de novo fecha.
- A coluna mostra a mesma conversa da página "Pergunte aos dados" (estado
  compartilhado), em formato compacto: frase, tabela curta e SQL recolhido;
  gráfico só na página inteira.
- **Contexto:** `agente.responder` ganha o parâmetro opcional
  `contexto: str | None`. Quando vem do painel, o texto é algo como "Contexto do
  painel: página Entrega e risco; período 01/01/2018 a 31/08/2018; região
  Nordeste." e vai ao modelo junto da pergunta, como instrução para filtrar por
  esse período e região quando a pergunta não disser outro. Na tela e no
  histórico aparece só a pergunta.
- Limites iguais: 300 caracteres, 20 perguntas por sessão (somando lateral e
  página), checagem de números, SQL visível.

### Visual

- Escuro como padrão (`?tema=claro` ou o botão troca). Fundo azul-marinho com
  brilho menta nos cantos.
- Cartões: ícone em quadrado colorido (menta, azul, violeta, âmbar), rótulo,
  valor grande, destaque com seta verde (melhora) ou vermelha (piora) e "vs. mês
  anterior". Para taxa de atraso, subir é piorar (seta vermelha).
- Gráficos: receita em área com degradê e o ano anterior em linha; barras
  horizontais por região com marca da taxa nacional; barras divergentes por UF
  (vermelho acima da taxa nacional, menta abaixo); tabelas HTML com destaque da
  probabilidade (vermelho a partir de 40%, âmbar de 30% a 40%, como a medida
  `Cor Prob. de Atraso` do Power BI).
- Barra lateral: marca, menu das 4 páginas com ícones, botão de tema, data dos
  dados.
- Celular: cartões em uma coluna; a coluna do agente vira seção abaixo do
  painel.

## Erros

- **Banco acordando** (primeira conexão falha): a página mostra "O banco está
  acordando" e um botão "Tentar de novo"; sem traceback.
- **Uma consulta falha:** só aquele visual mostra o aviso; os outros carregam.
- **Período sem dados:** cartão mostra "sem dados" (nunca zero inventado);
  gráfico e tabela mostram "Sem pedidos neste período".
- **Destaque sem mês anterior** (período começando em set/2016): sem seta, com
  "sem mês anterior".

## Testes

- **Números contra o Power BI:** teste de integração no CI que roda cada função
  de `painel/consultas.py` na janela padrão contra o banco do CI e compara com o
  caso correspondente de `dashboards/powerbi/conferencia/esperado.sql` (pedidos,
  receita, ticket médio, % no prazo, nota média, atraso em excesso do RJ,
  variação mensal, destaques da janela). Visuais sem caso ganham casos novos
  num `painel/conferencia/esperado.sql` próprio, no mesmo formato.
- **Unitários (sem banco):** filtros (padrão, limites, URL), texto do contexto,
  cartões (escape, seta e cor por direção, "sem dados"), formatos, montagem dos
  gráficos (tipo de marca, cores da paleta), parâmetros do SQL (nada do usuário
  concatenado).
- **App (AppTest):** as 4 páginas abrem sem exceção com banco e modelo
  substituídos; o botão "Tire sua dúvida" abre e fecha a coluna; pergunta feita
  na lateral aparece na página "Pergunte aos dados"; o contexto chega ao
  `responder` e não aparece na tela; o limite de 20 soma lateral e página.
- Conferência visual local nos dois temas antes de cada commit de tela.

## Riscos

- **CSS sobre nomes internos do Streamlit:** a versão segue fixada (1.65.0);
  atualizar é uma tarefa com conferência visual.
- **Cold start:** o Streamlit Cloud dorme sem uso e o Neon também; a primeira
  visita pode levar 30 s ou mais. Mitigação: aviso de "acordando" e cache.
- **Duas fontes da verdade das métricas** (DAX e SQL): o teste contra
  `esperado.sql` é o que impede divergência.
- **Cota do modelo:** perguntas da lateral consomem a mesma cota gratuita.

## Entrega

Branch `feat/painel-web` a partir da `main` depois do merge da Etapa 6; PR próprio
com CI verde; README e ROADMAP com a Etapa 7; GIF novo do painel com o agente.
