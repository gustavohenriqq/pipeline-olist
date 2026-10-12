# Etapa 8: HTML e CSS dentro do Power BI (desenho)

**Data:** 12/10/2026. **Status:** desenho aprovado em conversa; aguardando revisão
desta especificação.

## Por que

O dono quer o relatório do Power BI com o visual desenhado em HTML e CSS, como num
vídeo de referência (um relatório inteiro em HTML dentro do Power BI). É a peça
que mostra domínio de Power BI no portfólio; o painel web (Etapa 7) já é a vitrine
pública ao vivo.

Decisões do dono nesta conversa:

1. **Caminho:** HTML gerado por medidas DAX, desenhado pelo visual HTML Content.
   Não um visual próprio em TypeScript, nem só SVG nativo.
2. **Escopo:** redesenhar as 3 páginas existentes (Visão executiva, Entrega e
   risco, Vendedores) e incluir um dicionário de métricas, como o painel "Tire sua
   dúvida" de outro vídeo de referência.
3. **Publicação:** nada vai para o Service. O workspace disponível é da empresa
   do dono; publicar um projeto pessoal ali foi desaconselhado (o projeto ficaria
   no ambiente da empresa, e "Publicar na Web" exporia um link em nome dela). Se
   o dono tiver uma conta própria (estudante), a publicação vira tarefa separada.

**Critério de sucesso:** o relatório abre no Power BI Desktop com faixa, cartões e
tabelas em HTML no visual do painel web, os gráficos e filtros nativos continuam
funcionando, os números são os mesmos de antes (conferência automática verde) e
os prints novos saem pela exportação para PDF.

## Fora do escopo

- JavaScript dentro do HTML: o visual remove scripts. Abas e filtros continuam
  nativos (botões de navegação e segmentações).
- Publicação no Service e "Publicar na Web".
- Tema claro: o Power BI não tem botão de tema; fica o escuro do painel web.
- Agente de IA dentro do Power BI: o dicionário é texto versionado, não modelo de
  linguagem.

## O visual

**HTML Content (lite)**, a versão certificada do visual HTML Content (código aberto,
licença MIT). Certificado importa porque os prints saem pela exportação para PDF,
e visual não certificado pode sair em branco nela. Limites da versão lite:
conjunto reduzido de tags e nada carregado de fora (fontes, imagens por URL), então
os ícones são SVG escritos dentro do próprio HTML.

**Teste de viabilidade antes de tudo** (primeira tarefa do plano): importar o
visual de um arquivo `.pbiviz` (sem a loja, que pede a conta da organização) e
confirmar que (a) não pede a conta de trabalho e (b) aparece na exportação para
PDF do Desktop, com CSS inline (cores, bordas arredondadas, grid ou flex) e SVG.
O download do arquivo é pedido ao dono antes. Se (a) ou (b) falhar, a execução para
e volta ao dono com as opções: conta Microsoft gratuita para o login, ou o caminho
de SVG nativo por DAX.

O `.pbiviz` não é versionado no repositório; o relatório guarda a referência ao
visual, e o README explica de onde baixá-lo.

## O que vira HTML

| Página | Em HTML | Continua nativo |
|---|---|---|
| Visão executiva | Faixa do título (título, subtítulo, "mês de referência contra o anterior"); os 5 cartões (Receita, Pedidos, Ticket médio, % no prazo, Nota média) com ícone, valor, seta e cor; placar mensal com a variação colorida | Gráfico de receita e ano anterior; segmentações de período e região; botões de navegação |
| Entrega e risco | Faixa; 3 cartões (Taxa de atraso, Pedidos em alerta, Receita em risco); tabela de pedidos em andamento com linhas pintadas (vermelho a partir de 40%, âmbar a partir de 30%) | Gráficos de taxa por região e de excesso por UF; segmentação de período; navegação |
| Vendedores | Faixa; 3 cartões (Receita de itens, Itens, Taxa de atraso dos itens); tabela de vendedores com barra de receita proporcional em cada linha | Gráfico de grupos de categoria; segmentação de período; navegação |

## Medidas HTML

Pasta de exibição nova **HTML** em `_Medidas`. Cada medida monta uma string HTML e
**reaproveita as medidas que já existem** (`[Receita]`, `[Δ Receita]`,
`[Rótulo do Destaque]`, `[Cor Δ Receita]` e as demais): os números não mudam, só a
forma de mostrar. Formatação brasileira com `FORMAT` (mesmos formatos dos cartões
atuais).

- `HTML Faixa Executivo`, `HTML Faixa Entrega`, `HTML Faixa Vendedores`: uma por
  página, com título e subtítulo fixos (os mesmos de hoje) e o
  `[Rótulo do Destaque]`. Três medidas curtas são mais simples de ler que uma
  genérica com tabela de páginas.
- `HTML Cartões Executivo`, `HTML Cartões Entrega`, `HTML Cartões Vendedores`.
- `HTML Placar Mensal`, `HTML Pedidos em Risco`, `HTML Vendedores`: tabelas com
  `CONCATENATEX`, ordenadas como os visuais atuais e limitadas como eles.
- Textos que vêm do banco (rótulo do vendedor, categoria, UF) passam por um escape
  em DAX de `&`, `<` e `>` antes de entrar no HTML.

CSS sempre inline (o visual não aceita folha de estilo externa). Cores do painel
web: fundo azul-marinho escuro, menta como destaque, azul, violeta e âmbar de
apoio, vermelho para piora.

## Dicionário de métricas

- Tabela nova no modelo, **versionada em TMDL** (tabela calculada com
  `DATATABLE`), uma linha por métrica: `Métrica`, `O que é`, `Cálculo`, `Exemplo`,
  `Página`. Cobre as métricas que aparecem nos cartões e tabelas.
- Em cada página, um botão **Dicionário** mostra e esconde um painel lateral (dois
  indicadores, um com o painel e outro sem). No painel: segmentação com busca na
  coluna `Métrica` e um visual HTML com `HTML Dicionário`, que mostra cada métrica
  selecionada como cartão com "O que é", "Cálculo" e "Exemplo" (até 3 de uma vez;
  sem seleção, uma linha pedindo para escolher).
- A tabela não se relaciona com o resto do modelo e não entra no RLS.

## Identidade visual

O tema do relatório (`tema-olist.json`) passa a seguir o painel web: fundo da
página escuro, cores dos dados a partir de menta e azul, texto claro. Os visuais
nativos (gráficos, segmentações, botões) recebem esse tema para combinar com o
HTML.

## Testes

- **Conferência existente** (`dashboards/powerbi/conferencia/conferir.ps1`): os 29
  casos continuam passando; nenhuma medida existente muda.
- **Casos novos para o HTML** em `casos.json` (grupo `html`): na janela padrão,
  `HTML Cartões Executivo` contém "R$ 15,79 Mi" e "99.092" (formatos atuais do
  relatório); `HTML Pedidos em Risco` tem 50 linhas e as classes de cor esperadas;
  `HTML Dicionário` sem seleção mostra o pedido de escolha. O conferir passa a
  aceitar caso do tipo "contém texto", além de "igual ao número".
- **Escape:** caso com um rótulo contendo `&` (via `TREATAS` com valor construído)
  confirma `&amp;` na saída.
- **Conferência visual:** prints das 3 páginas e do dicionário aberto, exportados
  para PDF e convertidos em PNG como na Etapa 5, revisados antes do commit final.

## Riscos

- **Login ao importar o visual.** Mitigação: o teste de viabilidade vem primeiro e
  para tudo se pedir a conta de trabalho.
- **Visual em branco no PDF.** Mitigação: versão certificada (lite) e teste no
  primeiro passo.
- **Tags fora do conjunto da versão lite.** O teste de viabilidade cobre as que o
  desenho usa (div, span, table, svg com path, estilos inline).
- **DAX de texto difícil de manter.** Mitigação: uma medida por bloco, comentário
  `///` em cada uma e as medidas de número reaproveitadas, nunca recalculadas.

## Entrega

Branch `feat/powerbi-html`; PR próprio; `dashboards/powerbi/README.md`, README e
ROADMAP atualizados (Etapa 8 concluída); prints novos em `docs/prints/`.
