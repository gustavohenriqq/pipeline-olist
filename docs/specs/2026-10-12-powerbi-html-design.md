# Etapa 8: HTML e CSS dentro do Power BI (desenho)

**Data:** 12/10/2026. **Status:** aprovado; revisado no mesmo dia para o estilo
"premium" (seção "Revisão de estilo").

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
3. **Publicação:** pela **conta de estudante** do dono, não pela de trabalho (o
   workspace da empresa foi desaconselhado: o projeto ficaria no ambiente dela e o
   link público sairia em nome da organização). Com "Publicar na Web", qualquer
   pessoa abre o relatório sem login.

**Critério de sucesso:** o relatório abre no Power BI Desktop com as 3 páginas no
estilo da prévia aprovada (seção "Revisão de estilo"), os filtros e a navegação
nativos continuam funcionando e mudando os desenhos, os números são os mesmos de antes (conferência automática verde) e
os prints novos saem pela exportação para PDF. O relatório tem um link público
("Publicar na Web") aberto sem login, citado no README e no painel web.

## Fora do escopo

- JavaScript dentro do HTML: o visual remove scripts. Abas e filtros continuam
  nativos (botões de navegação e segmentações).
- Publicação pela conta de trabalho.
- Atualização agendada no Service: a base é estática, o relatório publicado guarda
  o retrato dos dados do momento da publicação.
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

## Revisão de estilo (12/10/2026)

Com o tema aplicado e os blocos antigos ainda no lugar, o dono achou o resultado
simples e trouxe referências de painéis "premium" (fundo azul-marinho profundo,
degradês ciano e violeta, anéis de porcentagem, gráficos de área com brilho, menu
lateral com ícones). Uma prévia da Visão executiva com os números reais foi aprovada:
[assets/2026-10-12-previa-executivo.html](assets/2026-10-12-previa-executivo.html).

Consequência: **os gráficos também passam a ser desenhados em SVG por DAX**, porque
os gráficos nativos não fazem degradê nem brilho. Custo aceito: esses gráficos não
têm dica ao passar o mouse nem filtro cruzado ao clicar. Segmentações (período,
região, dicionário) e navegação continuam nativas, e todos os desenhos respondem a
elas.

## O que vira HTML/SVG

| Página | Em HTML/SVG (medidas DAX) | Continua nativo |
|---|---|---|
| Todas | Menu lateral com ícones (página ativa destacada); cabeçalho com título e "mês de referência contra o anterior" | Botões de navegação transparentes sobre os ícones do menu; segmentações; botão do dicionário |
| Visão executiva | 3 cartões (Receita, Pedidos, Ticket médio) com seta e mini-gráfico de área; 2 anéis (% no prazo, Nota média) com seta; receita por mês em área com degradê, pontos com brilho, destaque do maior mês e ano anterior tracejado; taxa de atraso por região em barras com a linha da taxa nacional; 5 maiores grupos de categoria em barras | Período e região |
| Entrega e risco | Anel da taxa de atraso com seta; cartões de pedidos em alerta e receita em risco; barras da taxa por região com a linha nacional; barras divergentes do atraso em excesso por UF (vermelho acima, menta abaixo); tabela dos pedidos em andamento com linhas pintadas (vermelho a partir de 40%, âmbar a partir de 30%) | Período |
| Vendedores | Cartões de receita de itens (com seta e mini-gráfico), itens e taxa de atraso dos itens (anel); grupos de categoria em barras; tabela dos 50 vendedores com barra de receita em cada linha | Período |

O placar mensal da Visão executiva sai da página: o gráfico de receita e o
dicionário cobrem a leitura mês a mês.

## Medidas HTML

Pasta de exibição nova **HTML** em `_Medidas`. Cada medida monta uma string HTML e
**reaproveita as medidas que já existem** (`[Receita]`, `[Δ Receita]`,
`[Rótulo do Destaque]`, `[Cor Δ Receita]` e as demais): os números não mudam, só a
forma de mostrar. Formatação brasileira com `FORMAT` (mesmos formatos dos cartões
atuais).

- **Menu e cabeçalho, por página:** `HTML Menu Executivo`, `HTML Menu Entrega`,
  `HTML Menu Vendedores` (o ícone da página ativa destacado) e `HTML Cabeçalho
  Executivo`, `HTML Cabeçalho Entrega`, `HTML Cabeçalho Vendedores` (título,
  subtítulo e `[Rótulo do Destaque]`).
- **Cartões:** `HTML Cartões Executivo` (3 cartões com mini-gráfico e os 2 anéis),
  `HTML Cartões Entrega`, `HTML Cartões Vendedores`.
- **Gráficos em SVG:** `HTML Receita Mensal` (área com degradê, pontos, destaque do
  maior mês, ano anterior tracejado), `HTML Atraso por Região` (barras com a linha
  da taxa nacional; usada na Visão executiva e em Entrega e risco), `HTML Excesso
  por UF` (barras divergentes), `HTML Grupos Top 5` e `HTML Grupos` (todos os
  grupos, na página Vendedores).
- **Tabelas:** `HTML Pedidos em Risco`, `HTML Vendedores`, com `CONCATENATEX`,
  ordenadas e limitadas como as tabelas atuais (50 linhas).
- **Geometria do SVG em DAX:** a posição de cada ponto ou barra sai do valor sobre o
  máximo da série no recorte (`MAXX`), e a ordem do mês ou da categoria (`RANKX`),
  sempre dentro do filtro da página. Nenhum número é recalculado: as alturas vêm
  das medidas existentes.
- Textos que vêm do banco (rótulo do vendedor, categoria, UF) passam por um escape
  em DAX de `&`, `<` e `>` antes de entrar no HTML.

CSS sempre inline (o visual não aceita folha de estilo externa), com as cores da
seção "Identidade visual".

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

Paleta da prévia aprovada (vale para o HTML/SVG e para o tema do relatório):

| Papel | Cor |
|---|---|
| Fundo da página | `#070B1A` |
| Fundo dos blocos | `#121A3A` (degradê para `#17214A`) |
| Borda dos blocos | `rgba(130,150,255,0.14)` |
| Texto / texto suave | `#E8ECFF` / `#8E9AC8` |
| Destaque principal | degradê `#22D3EE` (ciano) para `#8B5CF6` (violeta) |
| Ano anterior, terceira série | `#EC4899` (rosa) |
| Melhora / piora | `#34D399` (menta) / `#F87171` (vermelho) |
| Referência (taxa nacional), alerta médio | `#FBBF24` (âmbar) |

O tema `tema-olist.json` leva o fundo, os textos e as cores dos dados, para os
visuais nativos (segmentações, botões) combinarem com o HTML.

## Testes

- **Conferência existente** (`dashboards/powerbi/conferencia/conferir.ps1`): os 29
  casos continuam passando; nenhuma medida existente muda.
- **Casos novos para o HTML** em `casos.json` (grupo `html`): na janela padrão,
  `HTML Cartões Executivo` contém "R$ 15,79 Mi" e "99.092" (formatos atuais do
  relatório); `HTML Pedidos em Risco` tem 50 linhas e as classes de cor esperadas;
  `HTML Dicionário` sem seleção mostra o pedido de escolha. O conferir passa a
  aceitar caso do tipo "contém texto", além de "igual ao número".
- **Gráficos em SVG:** `HTML Receita Mensal` na janela padrão tem um ponto por mês
  (20) e destaca nov/2017 ("R$ 1,18 Mi"); `HTML Atraso por Região` mostra Nordeste
  com "12,7%" ou o valor que `[Taxa de Atraso]` der, e a linha nacional; numa janela
  sem pedidos, cada gráfico mostra "sem dados" em vez de SVG vazio.
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

## Publicação

- **"Publicar na Web" não aceita modelo com RLS.** O relatório versionado mantém
  os papéis (Diretoria, Gerente regional, Vendedor) e o OLS; a versão pública é
  uma **cópia sem a pasta `roles`**, gerada por um script versionado
  (`dashboards/powerbi/gerar_versao_publica.ps1`) numa pasta fora do Git
  (`dashboards/powerbi/publico/`, no `.gitignore`), copiando também o cache de
  dados (`.pbi/cache.abf`) para não precisar atualizar. A tabela `seguranca_bi`
  só tem e-mails fictícios (`@exemplo.com.br`) e pode ir junto.
- **Passos do dono, com roteiro escrito:** entrar no Power BI Desktop com a conta
  de estudante, abrir a cópia pública, publicar no workspace pessoal ("Meu
  workspace") e, no Service, Arquivo > Inserir relatório > Publicar na Web. O
  Claude não interage com telas de login da Microsoft; confere o link depois.
- **Dependências da instituição:** o administrador do ambiente de estudante precisa
  permitir "Publicar na Web", e a licença precisa incluir o recurso. Se estiver
  bloqueado, a Etapa 8 fecha sem link público e isso fica registrado no README.
- **Depois do link:** README, `dashboards/powerbi/README.md` e a barra lateral do
  painel web ("Ver no Power BI") passam a apontar para ele.

## Entrega

Branch `feat/powerbi-html`; PR próprio; `dashboards/powerbi/README.md`, README e
ROADMAP atualizados (Etapa 8 concluída); prints novos em `docs/prints/`.
