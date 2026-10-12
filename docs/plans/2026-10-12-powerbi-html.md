# Etapa 8: HTML e CSS dentro do Power BI (plano de implementação)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** faixa, cartões e tabelas das 3 páginas do Power BI em HTML/CSS gerado por medidas DAX (visual HTML Content lite), com dicionário de métricas, tema do painel web e um link público pela conta de estudante.

**Architecture:** medidas novas na pasta "HTML" de `_Medidas.tmdl` montam strings HTML reaproveitando as medidas existentes; o relatório PBIR troca cartões, faixas e tabelas por visuais HTML Content; gráficos, segmentações e navegação continuam nativos. Conferência por DAX (`conferir.ps1`) ganha casos de "contém texto"; um teste Python confere a estrutura do PBIR.

**Tech Stack:** Power BI Desktop (PBIP: TMDL + PBIR), DAX, HTML Content (lite) `.pbiviz`, PowerShell (conferência), pytest (estrutura do relatório).

**Spec:** `docs/specs/2026-10-12-powerbi-html-design.md`

## Global Constraints

- Sem travessão (em dash) em nenhum texto gerado.
- Não usar a conta de trabalho; nada vai para o Service por ela. Publicação só pela conta de estudante, feita pelo dono.
- Nunca interagir com telas de login da Microsoft; o dono faz login e publicação. Screenshot antes de cada clique no menu Arquivo do Desktop.
- Nunca abrir uma segunda instância do Power BI Desktop; nunca encerrar processo que não foi aberto nesta sessão.
- Depois de editar TMDL/PBIR com o Desktop aberto: salvar no Desktop antes, editar, depois "Aplicar alterações externas" (o salvamento do Desktop sobrescreve edição externa).
- Download de arquivo (o `.pbiviz`) só com permissão explícita do dono, informando nome, origem e tamanho.
- O `.pbiviz` não é versionado; `dashboards/powerbi/publico/` vai para o `.gitignore`.
- Medidas existentes não mudam; medidas HTML reaproveitam `[Receita]`, `[Δ Receita]`, `[Rótulo do Destaque]`, `[Cor Δ ...]` e demais, nunca recalculam.
- Texto que vem do banco entra no HTML com escape de `&`, `<`, `>`.
- Cores do painel web (`agente/tema.py`, paleta escura): fundo `#0B1220`, superfície `#111A2C`, borda `#1F2A40`, texto `#E2E8F0`, texto suave `#94A3B8`, destaque `#34D399`, azul `#60A5FA`, violeta `#A78BFA`, âmbar `#FBBF24`, vermelho `#F87171`.
- Commit ao fim de cada task.

## Review Focus

1. Seleção vazia ou com muitas métricas no dicionário: sem seleção, uma linha pedindo para escolher; com mais de 3, mostra as 3 primeiras e diz quantas ficaram de fora. Teste na Task 6.
2. Filtro que zera um cartão (período sem pedidos, região sem dados): o HTML mostra "sem dados", nunca "R$ 0,00" inventado nem HTML quebrado. Teste na Task 3.
3. Rótulo do banco com `&`, `<` ou aspas: aparece literal. Teste na Task 3.
4. Segmentação de período mudando o mês de referência: faixa e cartões HTML acompanham (mesmo `[Rótulo do Destaque]`). Teste na Task 3 (caso com `CALCULATETABLE` em outra janela).
5. Exportação para PDF com o visual HTML: nenhum bloco em branco. Coberto pela Task 1 e pela conferência visual da Task 7.

---

### Task 1: viabilidade do visual HTML (porta de entrada)

**Files:**
- Nenhum arquivo versionado além do ledger; página de teste criada e removida no Desktop.

**Interfaces:**
- Produces: identificador do visual (`visualType` do HTML Content lite no PBIR, ex.: `htmlContent...`) e a lista de tags/CSS que renderizam no Desktop e no PDF, registrados no ledger; usados nas Tasks 4 a 6.

- [ ] **Step 1:** pedir ao dono permissão para baixar o `.pbiviz` do HTML Content (lite) da página oficial de releases do projeto (GitHub de Daniel Marsh-Patrick), informando nome, origem e tamanho; salvar fora do repositório (`%USERPROFILE%\Downloads\powerbi-visuais\`).
- [ ] **Step 2:** no Desktop já aberto com `Olist.pbip`, importar o visual de arquivo (painel Visualizações > "..." > Importar um visual de um arquivo). Expected: o visual aparece no painel **sem** pedir a conta de trabalho. Se pedir login: parar e levar ao dono (conta Microsoft gratuita ou caminho de SVG nativo).
- [ ] **Step 3:** criar uma página "teste html" com uma medida temporária que usa div com `display:flex`, `border-radius`, cor de fundo, `table`, e um `svg` com `path`; conferir no Desktop.
- [ ] **Step 4:** exportar para PDF (Arquivo > Exportar > PDF) e converter a página de teste em PNG. Expected: o bloco HTML aparece no PDF igual ao Desktop.
- [ ] **Step 5:** apagar a página e a medida de teste, salvar; registrar no ledger o `visualType` e o que renderizou (e o que não). `git status` sem mudança no relatório além do registro do visual importado.

### Task 2: tema escuro do painel web

**Files:**
- Modify: `dashboards/powerbi/Olist.Report/StaticResources/RegisteredResources/tema-olist.json`
- Create: `tests/test_powerbi_relatorio.py`

**Interfaces:**
- Produces: `tests/test_powerbi_relatorio.py` com helpers `_paginas() -> dict[str, dict]` (nome de exibição -> page.json) e `_visuais(pagina: str) -> list[dict]` (visual.json da página), usados nas Tasks 4 a 6.

- [ ] **Step 1: testes**

```python
def test_tema_segue_o_painel_web():
    tema = _tema()
    assert tema["background"] == "#0B1220"
    assert tema["foreground"] == "#E2E8F0"
    assert tema["dataColors"][:3] == ["#34D399", "#60A5FA", "#A78BFA"]

def test_tres_paginas_do_relatorio():
    assert set(_paginas()) == {"Executivo", "Entrega e risco", "Vendedores"}
```

- [ ] **Step 2:** rodar `.venv/Scripts/python.exe -m pytest tests/test_powerbi_relatorio.py -q`; Expected: o teste do tema falha (cores atuais azuis).
- [ ] **Step 3:** atualizar o tema (fundo, primeiro plano, `dataColors` = destaque, azul, violeta, âmbar, vermelho, texto suave; `textClasses` em texto claro; `visualStyles` com fundo de visual na superfície `#111A2C` e borda `#1F2A40`).
- [ ] **Step 4:** testes verdes; no Desktop, "Aplicar alterações externas" e conferir as 3 páginas; rodar `conferir.ps1` (29 casos verdes).
- [ ] **Step 5: commit** `feat(powerbi): tema escuro do painel web`.

### Task 3: medidas HTML e conferência de texto

**Files:**
- Modify: `dashboards/powerbi/Olist.SemanticModel/definition/tables/_Medidas.tmdl` (pasta "HTML")
- Modify: `dashboards/powerbi/conferencia/conferir.ps1`, `dashboards/powerbi/conferencia/casos.json`

**Interfaces:**
- Produces (medidas, pasta `HTML`): `HTML Faixa Executivo`, `HTML Faixa Entrega`, `HTML Faixa Vendedores`, `HTML Cartões Executivo`, `HTML Cartões Entrega`, `HTML Cartões Vendedores`, `HTML Placar Mensal`, `HTML Pedidos em Risco`, `HTML Vendedores`. Escape de texto do banco: o padrão `SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(x, "&", "&amp;"), "<", "&lt;"), ">", "&gt;")`, repetido onde entra texto (o modelo não usa funções DAX definidas pelo usuário).
- Produces (conferência): caso com `"contem": [..]` e opcional `"nao_contem": [..]` é conferido por substring, sem SQL; grupo novo `html` em `casos.json`, incluído no padrão de `-Grupos`.

- [ ] **Step 1: casos (grupo `html`)**

```json
{"caso": "html_cartoes_executivo", "dax": "EVALUATE ROW(\"v\", [HTML Cartões Executivo])",
 "contem": ["R$ 15,79 Mi", "99.092", "93,2%", "ago/2018"]},
{"caso": "html_cartoes_sem_dados", "dax": "EVALUATE ROW(\"v\", CALCULATE([HTML Cartões Executivo], dim_tempo[ano] = 2015))",
 "contem": ["sem dados"], "nao_contem": ["R$ 0"]},
{"caso": "html_faixa_outra_janela", "dax": "EVALUATE ROW(\"v\", CALCULATE([HTML Faixa Executivo], DATESBETWEEN(dim_tempo[data], DATE(2018,1,1), DATE(2018,3,31))))",
 "contem": ["mar/2018"]},
{"caso": "html_risco_linhas", "dax": "EVALUATE ROW(\"v\", [HTML Pedidos em Risco])",
 "contem": ["risco-alto", "#"], "nao_contem": ["<script"]},
{"caso": "html_escape", "dax": "EVALUATE ROW(\"v\", SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(\"A & <b>\", \"&\", \"&amp;\"), \"<\", \"&lt;\"), \">\", \"&gt;\"))",
 "contem": ["A &amp; &lt;b&gt;"]}
```

  O caso `html_risco_linhas` conta também 50 ocorrências de `<tr` no corpo (campo `"contagem": {"<tr": 51}` com o cabeçalho).
- [ ] **Step 2:** `conferir.ps1` passa a tratar `contem`, `nao_contem` e `contagem`; rodar `.\conferir.ps1 -Grupos html` com o Desktop aberto. Expected: os casos `html_*` falham (medidas não existem), os outros grupos continuam verdes.
- [ ] **Step 3:** escrever as medidas (CSS inline com as cores das Global Constraints; ícones em SVG inline; formatos iguais aos cartões atuais; "sem dados" quando a medida base é BLANK; tabelas com `CONCATENATEX` na mesma ordem e limite dos visuais atuais: placar por mês decrescente, risco 50 linhas por probabilidade decrescente com desempate pelo pedido, vendedores 50 por receita).
- [ ] **Step 4:** salvar no Desktop, aplicar alterações externas, rodar `.\conferir.ps1`. Expected: 29 casos antigos e os `html_*` verdes.
- [ ] **Step 5: commit** `feat(powerbi): medidas HTML e conferencia de texto`.

### Task 4: Visão executiva em HTML

**Files:**
- Modify: `dashboards/powerbi/Olist.Report/definition/pages/<Executivo>/visuals/*` (remove cartões/faixa/placar nativos, cria visuais HTML)
- Test: `tests/test_powerbi_relatorio.py`

**Interfaces:**
- Consumes: `visualType` da Task 1; medidas da Task 3; helpers da Task 2.

- [ ] **Step 1: teste**

```python
def test_executivo_usa_html_para_faixa_cartoes_e_placar():
    medidas = _medidas_html("Executivo")
    assert {"HTML Faixa Executivo", "HTML Cartões Executivo", "HTML Placar Mensal"} <= medidas
    assert not _tem_visual("Executivo", "cardVisual")  # cartoes nativos sairam
    assert _tem_visual("Executivo", "lineChart") or _tem_visual("Executivo", "areaChart")  # grafico nativo fica
```

- [ ] **Step 2:** rodar; Expected: falha.
- [ ] **Step 3:** no Desktop (salvar antes), substituir os visuais: um HTML Content por bloco, ligado à medida; manter gráfico, segmentações e botões de navegação; posições no mesmo grid de hoje.
- [ ] **Step 4:** salvar; teste verde; `conferir.ps1` verde; conferência visual da página no Desktop.
- [ ] **Step 5: commit** `feat(powerbi): visao executiva em HTML`.

### Task 5: Entrega e risco e Vendedores em HTML

**Files:** páginas `<Entrega e risco>` e `<Vendedores>` do PBIR; `tests/test_powerbi_relatorio.py`.

- [ ] **Step 1: testes** `test_entrega_usa_html` (`HTML Faixa Entrega`, `HTML Cartões Entrega`, `HTML Pedidos em Risco`; gráficos de região e UF continuam nativos) e `test_vendedores_usa_html` (`HTML Faixa Vendedores`, `HTML Cartões Vendedores`, `HTML Vendedores`; gráfico de grupos nativo).
- [ ] **Step 2:** rodar; Expected: falham.
- [ ] **Step 3:** substituir os visuais como na Task 4.
- [ ] **Step 4:** testes, `conferir.ps1` e conferência visual verdes.
- [ ] **Step 5: commit** `feat(powerbi): entrega, risco e vendedores em HTML`.

### Task 6: dicionário de métricas

**Files:**
- Create: `dashboards/powerbi/Olist.SemanticModel/definition/tables/dicionario_metricas.tmdl` (tabela calculada `DATATABLE`)
- Modify: `_Medidas.tmdl` (`HTML Dicionário`), as 3 páginas (botão, painel, indicadores), `casos.json`, `tests/test_powerbi_relatorio.py`

**Interfaces:**
- Produces: tabela `dicionario_metricas` (`Métrica`, `O que é`, `Cálculo`, `Exemplo`, `Página`), sem relacionamento; medida `HTML Dicionário`; indicadores `Dicionário aberto` e `Dicionário fechado` por página.

- [ ] **Step 1: casos e teste**

```json
{"caso": "html_dicionario_sem_selecao", "dax": "EVALUATE ROW(\"v\", [HTML Dicionário])", "contem": ["Escolha uma métrica"]},
{"caso": "html_dicionario_uma", "dax": "EVALUATE ROW(\"v\", CALCULATE([HTML Dicionário], dicionario_metricas[Métrica] = \"Taxa de atraso\"))", "contem": ["Taxa de atraso", "Cálculo", "Exemplo"]},
{"caso": "html_dicionario_muitas", "dax": "EVALUATE ROW(\"v\", CALCULATE([HTML Dicionário], dicionario_metricas[Métrica] IN {\"Receita\", \"Pedidos\", \"Ticket médio\", \"% no prazo\"}))", "contem": ["e mais 1"]}
```

```python
def test_dicionario_em_todas_as_paginas():
    for pagina in ("Executivo", "Entrega e risco", "Vendedores"):
        assert "HTML Dicionário" in _medidas_html(pagina)
        assert _tem_segmentacao(pagina, "dicionario_metricas", "Métrica")
```

- [ ] **Step 2:** rodar; Expected: falham.
- [ ] **Step 3:** tabela com uma linha por métrica dos cartões e tabelas (definições conferidas contra as medidas DAX e contra `docs/painel-web.md`); `HTML Dicionário` (sem seleção pede para escolher; até 3 cartões; acima de 3, "e mais N"); botão "Dicionário" e painel lateral (segmentação com busca + HTML) com dois indicadores por página.
- [ ] **Step 4:** casos e teste verdes; conferência visual abrindo e fechando o painel nas 3 páginas.
- [ ] **Step 5: commit** `feat(powerbi): dicionario de metricas`.

### Task 7: prints, versão pública, documentação e PR

**Files:**
- Create: `dashboards/powerbi/gerar_versao_publica.ps1`
- Modify: `.gitignore` (`dashboards/powerbi/publico/`), `dashboards/powerbi/README.md`, `README.md`, `ROADMAP.md`, `docs/prints/powerbi-*.png`, `docs/prints/powerbi-olist.pdf`

- [ ] **Step 1:** `gerar_versao_publica.ps1`: copia `Olist.pbip`, `Olist.Report` e `Olist.SemanticModel` (com `.pbi/cache.abf`) para `dashboards/powerbi/publico/`, sem `definition/roles/`; falha se a pasta de origem não existir. Teste: rodar e conferir que `publico/Olist.SemanticModel/definition/roles` não existe e `tables/` é igual ao original.
- [ ] **Step 2:** exportar o PDF das 3 páginas e do dicionário aberto; converter em PNG (mesmo processo da Etapa 5); conferência visual.
- [ ] **Step 3:** docs (o que é HTML por DAX, por que lite, limites, como importar o `.pbiviz`, conferência de texto, versão pública) e roteiro de publicação para o dono (abrir `publico/Olist.pbip`, entrar com a conta de estudante, publicar em "Meu workspace", no Service: Arquivo > Inserir relatório > Publicar na Web).
- [ ] **Step 4:** varredura de segredo; PR; CI verde; revisão final independente.

### Task 8: publicação (passos do dono) e links

**Files:**
- Modify: `agente/app.py` (link "Ver no Power BI" na barra lateral), `tests/test_painel_app.py`, `README.md`, `dashboards/powerbi/README.md`

- [ ] **Step 1:** o dono publica seguindo o roteiro. Se o ambiente bloquear "Publicar na Web", registrar no README e encerrar sem link.
- [ ] **Step 2: teste** `test_barra_lateral_tem_link_do_power_bi`: com `POWERBI_PUBLICO` definido (constante em `painel/comum.py`), a barra lateral tem um link com esse endereço e o texto "Ver no Power BI".
- [ ] **Step 3:** rodar; Expected: falha. Implementar; teste verde; suíte verde.
- [ ] **Step 4:** abrir o link público num navegador sem login e conferir as 3 páginas; README e `dashboards/powerbi/README.md` com o link.
- [ ] **Step 5:** commit; merge depois do aceite do dono.
