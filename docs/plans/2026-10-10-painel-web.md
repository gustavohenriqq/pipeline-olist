# Etapa 7: painel web com o agente junto (plano de implementação)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** o app público (`agente/app.py`) vira painel + agente: 3 páginas com os números do Power BI, filtros, visual em HTML/CSS e o agente numa coluna lateral que conhece a página e os filtros.

**Architecture:** roteador `st.navigation` em `agente/app.py`; pacote novo `painel/` com filtros, consultas SQL parametrizadas, cartões HTML, gráficos Altair e a coluna do agente. Mesma conexão só de leitura do agente; números conferidos contra `dashboards/powerbi/conferencia/esperado.sql`.

**Tech Stack:** Python 3.11, Streamlit 1.65.0, Altair, pandas, psycopg2, PostgreSQL (Neon), pytest + AppTest.

**Spec:** `docs/specs/2026-10-10-painel-web-design.md`

## Global Constraints

- Sem travessão (em dash) em nenhum texto gerado, código ou doc.
- Não citar empresas em arquivos versionados além dos produtos já usados no projeto.
- Nenhum segredo no Git; varredura `npg_|AIza|gsk_|AQ\.` antes de cada commit que toca configuração.
- `streamlit==1.65.0` fixo em `agente/requirements.txt`; o ponto de entrada continua `agente/app.py`.
- SQL do painel sempre parametrizado (`%s` com `parametros`); nenhum texto do usuário concatenado em SQL.
- Painel lê só pelo usuário `agente_leitura` e por `banco.executar` (transação read-only, timeout).
- Textos da interface em português do Brasil; números no formato brasileiro (`agente/apresentacao.py`).
- Janela padrão 01/01/2017 a 31/08/2018; limites do seletor 01/09/2016 a 31/10/2018.
- Tema escuro é o padrão; `?tema=claro` ou o botão troca.
- Testes: `.venv/Scripts/python.exe -m pytest tests --ignore=tests/integracao -q` (unitários) e `tests/integracao` (CI, Postgres com a amostra).
- Branch `feat/painel-web` a partir da `main` depois do merge da Etapa 6; commit ao fim de cada task.

## Review Focus

1. Seleção parcial ou invertida no seletor de período (o `date_input` devolve uma data só enquanto o usuário escolhe a segunda): o painel mantém o período anterior, sem exceção. Teste na Task 1.
2. Período sem mês anterior com dados (começando em set/2016) ou região sem pedidos no mês: destaque mostra "sem mês anterior", nunca divisão por zero. Testes nas Tasks 2 e 4.
3. Texto vindo do banco com `<`, `&` ou `$` em cartões e tabelas (rótulo de vendedor, categoria): aparece literal, não vira HTML nem fórmula. Teste na Task 4.
4. Cache por filtros: `Filtros` precisa ser hashável e dois filtros iguais devem cair na mesma chave. Teste na Task 1.
5. Neon dormindo na primeira visita do painel: aviso "O banco está acordando" com "Tentar de novo"; uma consulta que falha não derruba as outras. Teste na Task 5.

---

### Task 1: filtros e consulta parametrizada

**Files:**
- Modify: `agente/banco.py` (`executar` ganha `parametros`)
- Create: `painel/__init__.py`, `painel/filtros.py`
- Test: `tests/test_painel_filtros.py`, `tests/integracao/test_painel_numeros.py` (só o caso do `executar` com parâmetro nesta task)

**Interfaces:**
- Produces:
  - `banco.executar(conexao, sql: str, parametros: tuple | None = None) -> tuple[list[str], list[tuple]]` (compatível com as chamadas atuais)
  - `@dataclass(frozen=True) Filtros(inicio: date, fim: date, regiao: str | None = None)`
  - `filtros.PADRAO: Filtros` = `Filtros(date(2017,1,1), date(2018,8,31), None)`; `filtros.MINIMO = date(2016,9,1)`; `filtros.MAXIMO = date(2018,10,31)`; `filtros.REGIOES = ("Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")`
  - `filtros.mes_referencia(f: Filtros) -> str` ('AAAA-MM' do mês de `f.fim`)
  - `filtros.mes_anterior(ano_mes: str) -> str`
  - `filtros.da_selecao(valor, atual: Filtros) -> Filtros` (aplica o retorno do `date_input`)
  - `filtros.da_url(params: dict) -> Filtros`, `filtros.para_url(f: Filtros) -> dict[str, str]`
  - `filtros.contexto(pagina: str, f: Filtros) -> str`

- [ ] **Step 1: testes de filtros**

```python
def test_padrao_e_mes_de_referencia():
    assert PADRAO == Filtros(date(2017, 1, 1), date(2018, 8, 31), None)
    assert mes_referencia(PADRAO) == "2018-08"
    assert mes_anterior("2018-01") == "2017-12"

def test_selecao_parcial_ou_invertida_mantem_o_atual():
    assert da_selecao((date(2018, 1, 1),), PADRAO) == PADRAO
    assert da_selecao(date(2018, 1, 1), PADRAO) == PADRAO
    assert da_selecao((date(2018, 5, 1), date(2018, 1, 1)), PADRAO) == Filtros(date(2018, 1, 1), date(2018, 5, 1), None)

def test_selecao_fora_dos_limites_e_cortada():
    f = da_selecao((date(2015, 1, 1), date(2019, 1, 1)), PADRAO)
    assert (f.inicio, f.fim) == (MINIMO, MAXIMO)

def test_filtros_iguais_tem_o_mesmo_hash():
    assert hash(Filtros(date(2018, 1, 1), date(2018, 2, 1), "Sul")) == hash(Filtros(date(2018, 1, 1), date(2018, 2, 1), "Sul"))

def test_url_ida_e_volta_e_lixo_cai_no_padrao():
    f = Filtros(date(2018, 1, 1), date(2018, 3, 31), "Nordeste")
    assert da_url(para_url(f)) == f
    assert da_url({"inicio": "abc", "regiao": "Marte"}) == PADRAO

def test_contexto_para_o_agente():
    texto = contexto("Entrega e risco", Filtros(date(2018, 1, 1), date(2018, 8, 31), "Nordeste"))
    assert texto == "Contexto do painel: página Entrega e risco; período 01/01/2018 a 31/08/2018; região Nordeste."
    assert "região" not in contexto("Vendedores", PADRAO)
```

- [ ] **Step 2: rodar e ver falhar**: `.venv/Scripts/python.exe -m pytest tests/test_painel_filtros.py -q` → erro de importação de `painel.filtros`.
- [ ] **Step 3: teste de integração do parâmetro** em `tests/integracao/test_painel_numeros.py`: fixture `conexao` como a `admin` de `test_agente_permissoes.py` (skip sem Postgres); `executar(conexao, "select %s::int + 1", (41,))` devolve `(["?column?"], [(42,)])`. Rodar: falha com `TypeError` (sem Postgres local: skip; confirmar no CI).
- [ ] **Step 4: implementar** `painel/filtros.py` e o parâmetro em `banco.executar` (`cur.execute(sql, parametros)`).
- [ ] **Step 5: rodar** os dois arquivos → PASS; suíte unitária inteira verde.
- [ ] **Step 6: commit** `feat(painel): filtros do painel e consulta parametrizada`.

### Task 2: números da Visão executiva

**Files:**
- Create: `painel/consultas.py`
- Test: `tests/test_painel_consultas.py`, `tests/integracao/test_painel_numeros.py`

**Interfaces:**
- Consumes: `Filtros`, `mes_referencia`, `mes_anterior`, `banco.executar(conexao, sql, parametros)`
- Produces (todas `(conexao, f: Filtros) -> pandas.DataFrame`, colunas exatas):
  - `cartoes_executivo` → 1 linha: `receita, pedidos, ticket_medio, pct_no_prazo, nota_media, receita_ref, receita_ant, pedidos_ref, pedidos_ant, ticket_ref, ticket_ant, pct_ref, pct_ant, nota_ref, nota_ant` (`*_ref` = mês de referência, `*_ant` = mês anterior, `None` sem dados)
  - `receita_mensal` → `ano_mes, receita, receita_ano_anterior`
  - `placar_mensal` → `ano_mes, receita, variacao_mensal, pedidos, ticket_medio, pct_no_prazo` (mais recente primeiro)
  - `delta(ref, ant, *, taxa: bool) -> float | None` (valor: `ref/ant - 1`; taxa: `(ref - ant) * 100` em pontos; `None` se faltar algum ou `ant == 0` em valor)

Definições (iguais às medidas do Power BI): período por `purchased_at::date between %s and %s`; região por `dim_clientes.regiao = %s` só quando `f.regiao`; pedidos = `count(distinct order_id)`; receita = `sum(valor_total)`; % no prazo = média de `entregue_no_prazo` só nos não nulos; nota = `avg(nota_avaliacao)`.

- [ ] **Step 1: testes unitários** com conexão falsa que grava `(sql, parametros)`:

```python
def test_filtro_vai_como_parametro_nunca_no_texto():
    f = Filtros(date(2018, 1, 1), date(2018, 8, 31), "Nordeste")
    sql, params = _executa(cartoes_executivo, f)
    assert "Nordeste" not in sql and "2018-01-01" not in sql
    assert "Nordeste" in params and date(2018, 1, 1) in params

def test_delta_de_valor_e_de_taxa():
    assert delta(110.0, 100.0, taxa=False) == pytest.approx(0.10)
    assert delta(0.95, 0.93, taxa=True) == pytest.approx(2.0)
    assert delta(10.0, None, taxa=False) is None
    assert delta(10.0, 0.0, taxa=False) is None
```

- [ ] **Step 2: teste de integração contra o Power BI** em `tests/integracao/test_painel_numeros.py`: fixture `esperado` roda `dashboards/powerbi/conferencia/esperado.sql` e devolve `dict[caso, str]`.

```python
TUDO = Filtros(date(2016, 9, 1), date(2018, 10, 31), None)

def test_cartoes_na_base_inteira_batem_com_o_power_bi(conexao, esperado):
    c = cartoes_executivo(conexao, TUDO).iloc[0]
    assert c.pedidos == int(esperado["pedidos"])
    assert c.receita == pytest.approx(float(esperado["receita"]), abs=0.01)
    assert c.ticket_medio == pytest.approx(float(esperado["ticket_medio"]), abs=0.0001)
    assert c.pct_no_prazo == pytest.approx(float(esperado["pct_no_prazo"]), abs=1e-9)
    assert c.nota_media == pytest.approx(float(esperado["nota_media"]), abs=1e-9)

def test_destaques_da_janela_padrao(conexao, esperado):
    c = cartoes_executivo(conexao, PADRAO).iloc[0]
    assert delta(c.receita_ref, c.receita_ant, taxa=False) == pytest.approx(float(esperado["delta_receita_janela"]), abs=1e-9)
    assert delta(c.pct_ref, c.pct_ant, taxa=True) == pytest.approx(float(esperado["delta_pct_no_prazo_janela"]), abs=1e-9)

def test_variacao_mensal_de_marco(conexao, esperado):
    p = placar_mensal(conexao, TUDO).set_index("ano_mes")
    assert p.loc["2018-03", "variacao_mensal"] == pytest.approx(float(esperado["variacao_mensal_2018_03"]), abs=1e-9)
```

  Se a amostra do CI não tiver pedido em algum mês citado, o caso faz `pytest.skip` com o motivo (o `esperado.sql` devolve nulo).
- [ ] **Step 3: rodar e ver falhar** (unitário: importação; integração: no CI).
- [ ] **Step 4: implementar** `painel/consultas.py` (Executivo).
- [ ] **Step 5: rodar** unitários → PASS; integração local se houver Postgres, senão no CI do PR.
- [ ] **Step 6: commit** `feat(painel): numeros da visao executiva conferidos contra o Power BI`.

### Task 3: números de Entrega e risco e de Vendedores

**Files:**
- Modify: `painel/consultas.py`
- Create: `painel/conferencia/esperado.sql`
- Test: `tests/test_painel_consultas.py`, `tests/integracao/test_painel_numeros.py`

**Interfaces:**
- Produces (`(conexao, f) -> DataFrame`):
  - `cartoes_entrega` → `taxa_atraso, taxa_ref, taxa_ant, pedidos_alerta, receita_risco`
  - `taxa_por_regiao` → `regiao, taxa_atraso, taxa_nacional`
  - `excesso_por_uf` → `uf, atraso_em_excesso` (maior para menor)
  - `pedidos_em_risco` → `pedido, compra, entrega_prevista, uf, valor, prob_atraso` (`conjunto = 'em_andamento'`, maior probabilidade primeiro, `LIMIT 50`; `pedido` = `'#' || left(order_id, 10)` como no Power BI)
  - `cartoes_vendedores` → `receita_itens, itens, taxa_atraso_itens, receita_ref, receita_ant`
  - `receita_por_grupo` → `categoria_grupo, receita_itens`
  - `vendedores` → `vendedor, receita_itens, itens, taxa_atraso_itens` (`LIMIT 50`, maior receita primeiro)

Definições: taxa de atraso = média de `not entregue_no_prazo` nos não nulos; taxa nacional = mesma taxa no período sem filtro de região; excesso = atrasos da UF - entregues da UF * taxa nacional; alerta e receita em risco com `alerta` e `conjunto in ('teste','em_andamento')`, filtrados pelo período de compra; itens filtrados por `fato_itens_pedido.tempo_sk_compra` → `dim_tempo.data`; atraso dos itens pelo `entregue_no_prazo` do pedido do item.

- [ ] **Step 1: casos novos** em `painel/conferencia/esperado.sql`, mesmo formato `caso | valor`, escritos à mão sem reaproveitar o SQL do painel: `taxa_regiao_nordeste`, `taxa_nacional`, `primeira_uf_excesso`, `itens`, `receita_itens`, `taxa_atraso_itens`, `primeiro_grupo`, `receita_primeiro_grupo`, `primeiro_vendedor`, `pedidos_em_risco_linhas`.
- [ ] **Step 2: testes de integração**: na base inteira (`TUDO`), `cartoes_entrega` bate com `pedidos_alerta` e `receita_risco` do `esperado.sql` do Power BI; `excesso_por_uf` na linha `RJ` bate com `excesso_rj`; os demais visuais batem com os casos do Step 1. Unitário: todos os novos usam parâmetros (mesma checagem da Task 2).
- [ ] **Step 3: rodar e ver falhar.**
- [ ] **Step 4: implementar.**
- [ ] **Step 5: rodar** → PASS (integração no CI se não houver Postgres local).
- [ ] **Step 6: commit** `feat(painel): numeros de entrega, risco e vendedores`.

### Task 4: cartões, gráficos e tema do painel

**Files:**
- Create: `painel/cartoes.py`, `painel/graficos.py`
- Modify: `agente/tema.py` (escuro como padrão, CSS de cartões, menu e popovers), `.streamlit/config.toml` (`base = "dark"`, menta)
- Test: `tests/test_painel_visual.py`, `tests/test_agente_tema.py`

**Interfaces:**
- Consumes: `apresentacao.numero_br`, `apresentacao.tabela_html`, `apresentacao.formatadores`, `tema.PALETAS`, `consultas.delta`
- Produces:
  - `cartao(rotulo: str, valor: str, icone: str, cor: str, variacao: float | None = None, *, taxa: bool = False, piora_quando_sobe: bool = False, sem_anterior: bool = False) -> str` (HTML; `cor` em `{"menta","azul","violeta","ambar"}`; `icone` = nome Material Symbols)
  - `linha_de_cartoes(cartoes: list[str]) -> str`
  - `valor_br(valor, tipo: str) -> str` com `tipo` em `{"moeda_compacta","inteiro","moeda","pct","nota"}` (R$ 15,79 mi; 99.092; R$ 159,31; 93,2%; 4,09); `None` → "sem dados"
  - `graficos.receita_com_ano_anterior(df, paleta)`, `graficos.barras_regiao(df, paleta)`, `graficos.excesso_divergente(df, paleta)`, `graficos.barras_horizontais(df, rotulo, valor, paleta)` → `alt.Chart`
  - `tema.tema_valido(None) == "escuro"`

- [ ] **Step 1: testes**

```python
def test_cartao_escapa_texto_e_mostra_seta():
    html = cartao("<b>Receita</b>", "R$ 15,79 mi", "payments", "menta", -0.052)
    assert "&lt;b&gt;Receita&lt;/b&gt;" in html and "<b>Receita</b>" not in html
    assert "5,2%" in html and "vs. mês anterior" in html and "piora" in html

def test_taxa_de_atraso_subindo_e_piora_em_pontos():
    html = cartao("Taxa de atraso", "6,8%", "schedule", "ambar", 2.8, taxa=True, piora_quando_sobe=True)
    assert "2,8 pp" in html and "piora" in html

def test_sem_mes_anterior_e_sem_dados():
    assert "sem mês anterior" in cartao("Receita", "R$ 1,00", "payments", "menta", None, sem_anterior=True)
    assert valor_br(None, "moeda") == "sem dados"
    assert valor_br(15786203.57, "moeda_compacta") == "R$ 15,79 mi"

def test_excesso_divergente_pinta_acima_e_abaixo():
    df = pd.DataFrame({"uf": ["RJ", "SP"], "atraso_em_excesso": [659.0, -923.0]})
    spec = excesso_divergente(df, PALETAS["escuro"]).to_dict()
    assert spec["mark"]["type"] == "bar"
    assert "condition" in spec["encoding"]["color"] or spec["encoding"]["color"].get("scale")

def test_tema_padrao_escuro():
    assert tema_valido(None) == "escuro"
```

  Atualizar `test_tema_comeca_claro_e_alterna` (agora começa escuro) na mesma task.
- [ ] **Step 2: rodar e ver falhar.**
- [ ] **Step 3: implementar.** Cartão: ícone em quadrado na cor do cartão, rótulo, valor, variação com seta (verde melhora, vermelho piora); CSS em `tema.py` para `.cartao`, `.cartoes`, menu do `st.navigation`, popovers do `selectbox` e `date_input` nos dois temas.
- [ ] **Step 4: rodar** a suíte unitária → PASS.
- [ ] **Step 5: conferência visual** local (`preview_start agente`) de uma página de teste nos dois temas antes do commit.
- [ ] **Step 6: commit** `feat(painel): cartoes, graficos e tema escuro padrao`.

### Task 5: páginas do painel e roteador

**Files:**
- Modify: `agente/app.py` (vira roteador; o chat atual sai para `painel/paginas/pergunte.py`)
- Create: `painel/paginas/__init__.py`, `executivo.py`, `entrega.py`, `vendedores.py`, `pergunte.py`, `painel/comum.py`
- Test: `tests/test_painel_app.py`, `tests/test_agente_app.py` (ajustado à navegação)

**Interfaces:**
- Consumes: Tasks 1 a 4.
- Produces:
  - `comum.filtros_da_pagina(regiao: bool) -> Filtros` (widgets de período e região; estado em `st.session_state["filtros"]` e na URL)
  - `comum.carregar(funcao, f: Filtros) -> pandas.DataFrame | None` (cache `st.cache_data(ttl=3600)` por `(funcao.__name__, f)`; falha de conexão vira aviso "O banco está acordando" com botão "Tentar de novo"; erro de uma consulta vira `st.warning` só daquele visual e devolve `None`)
  - `comum.cabecalho(titulo: str, subtitulo: str, pagina: str)` (título, subtítulo e o botão "Tire sua dúvida", chave `abrir_agente`)
  - páginas registradas em `agente/app.py` com `st.Page(..., title=..., icon=":material/...:", default=True)` só na Visão executiva

- [ ] **Step 1: testes (AppTest, banco e consultas substituídos por DataFrames fixos)**

```python
def test_quatro_paginas_abrem_sem_excecao(ambiente): ...  # switch_page para cada uma; not at.exception
def test_visao_executiva_mostra_cinco_cartoes(ambiente): ...  # 5 ocorrências de 'class="cartao' no markdown
def test_consulta_que_falha_nao_derruba_a_pagina(ambiente): ...  # uma função levanta ErroBanco; warning daquele visual; demais cartões presentes
def test_banco_acordando_mostra_aviso_e_tentar_de_novo(ambiente): ...  # abrir_conexao levanta OSError; aviso + botão
def test_periodo_sem_dados_mostra_sem_dados(ambiente): ...  # DataFrames vazios; "sem dados" e "Sem pedidos neste período"
```

- [ ] **Step 2: rodar e ver falhar.**
- [ ] **Step 3: implementar.** Layout de cada página como na spec; textos de título e subtítulo iguais aos do Power BI; barra lateral com marca, menu, tema e data dos dados.
- [ ] **Step 4: rodar** a suíte unitária → PASS.
- [ ] **Step 5: conferência visual** local das 4 páginas nos dois temas e em largura de celular (375 px).
- [ ] **Step 6: commit** `feat(painel): tres paginas do painel e menu`.

### Task 6: agente ao lado do painel

**Files:**
- Modify: `agente/agente.py` (`responder` ganha `contexto`), `painel/paginas/pergunte.py`
- Create: `painel/lateral.py`
- Test: `tests/test_agente_fluxo.py`, `tests/test_painel_app.py`

**Interfaces:**
- Consumes: `filtros.contexto`, `comum.cabecalho`
- Produces:
  - `agente.responder(pergunta, historico, llm, executar, esquema, contexto: str | None = None) -> Resposta` (contexto entra na mensagem do usuário para o modelo gerar o SQL, como "Pergunta: ...\n<contexto> Use esse período e região se a pergunta não disser outro."; não entra em `Turno` nem na tela)
  - `lateral.coluna_do_agente(pagina: str, f: Filtros)` (chat compacto: frase, tabela curta, SQL recolhido; sem gráfico)
  - estado compartilhado `conversa`, `historico`, `perguntas_feitas` entre lateral e página

- [ ] **Step 1: testes**

```python
def test_contexto_vai_ao_modelo_mas_nao_ao_historico():  # test_agente_fluxo.py, com llm falso que grava as mensagens
    ...
    assert "período 01/01/2018 a 31/08/2018" in mensagens_enviadas[-1]["content"]
    assert "Contexto do painel" not in resposta.texto

def test_tire_sua_duvida_abre_e_fecha(ambiente): ...
def test_pergunta_da_lateral_aparece_na_pagina_pergunte(ambiente): ...
def test_responder_recebe_o_contexto_da_pagina_e_dos_filtros(ambiente): ...
def test_limite_de_20_soma_lateral_e_pagina(ambiente): ...
```

- [ ] **Step 2: rodar e ver falhar.**
- [ ] **Step 3: implementar.** Coluna à direita com `st.columns([3, 1.3])` quando aberta; no celular a coluna vem abaixo (CSS).
- [ ] **Step 4: rodar** a suíte unitária → PASS.
- [ ] **Step 5: conferência real** local com a chave: na Entrega e risco filtrada em Nordeste/2018, perguntar "qual UF teve mais atrasos?" e conferir que o SQL gerado filtra Nordeste e 2018.
- [ ] **Step 6: commit** `feat(painel): agente ao lado do painel com o contexto da tela`.

### Task 7: documentação, publicação e fechamento

**Files:**
- Modify: `README.md` (seção da Etapa 7, link, GIF), `ROADMAP.md` (Etapa 7 concluída, Etapa 8 planejada), `docs/agente.md` (o agente agora mora no painel)
- Create: `docs/painel-web.md` (páginas, definições, conferência, limites), `docs/prints/painel.gif`

- [ ] **Step 1:** avaliação do agente (`python -m agente.avaliacao.avaliar`) continua 25/25 ou cada diferença é explicada em `docs/agente.md`.
- [ ] **Step 2:** GIF do painel: Visão executiva, troca de período, Entrega e risco, "Tire sua dúvida" com uma pergunta, tema claro.
- [ ] **Step 3:** docs e varredura de segredo (`git grep -n -i -E "npg_|AIza|gsk_|password\s*=" -- . ':!*.example'`).
- [ ] **Step 4:** PR, CI verde (inclui os testes de integração contra o `esperado.sql`), revisão final independente, merge depois do aceite do dono; o app do Streamlit Cloud já aponta para `main`.
