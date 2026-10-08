# Etapa 5: Power BI avançado

Especificação de desenho. Data: 08/10/2026. Estado: desenho aprovado em conversa;
aguardando revisão deste documento.

## 1. Objetivo

Um relatório executivo no Power BI Desktop, ligado ao star schema, com os recursos
que o mercado cobra de um modelo corporativo: DAX com inteligência de tempo, RLS
dinâmico e OLS. O relatório não é publicado no Power BI Service (decisão do dono:
a conta de trabalho não é usada para projeto pessoal). A entrega é o projeto
versionado, prints e um PDF exportado.

**Critérios de sucesso:**

1. O projeto está em formato PBIP em `dashboards/powerbi/`, com o modelo em TMDL e
   o relatório em PBIR, e abre no Power BI Desktop sem erro.
2. Atualizado contra o Postgres local, os números batem com o SQL (tabela de
   conferência da seção 9).
3. Cada perfil de segurança, testado com "Exibir como", vê exatamente o recorte
   esperado, conferido por uma contagem em SQL.
4. O perfil Vendedor não enxerga as colunas de identificação do cliente (OLS).
5. Três páginas prontas, com prints no README e um PDF exportado.
6. `dashboards/powerbi/README.md` documenta modelo, medidas, segurança e
   conferência; README e ROADMAP marcam a Etapa 5 como concluída.

Restrições: sem publicar no Service, sem ferramenta paga, sem travessão em texto,
sem citar empresas além do dataset.

## 2. Formato: PBIP

```
dashboards/powerbi/
  Olist.pbip
  Olist.SemanticModel/
    definition/
      model.tmdl
      expressions.tmdl            parâmetros do Power Query
      relationships.tmdl
      roles/*.tmdl                RLS e OLS
      tables/*.tmdl               uma por tabela, com colunas e medidas
  Olist.Report/
    definition/                   PBIR: páginas e visuais em JSON
    StaticResources/              tema
  README.md
```

**Por que PBIP.** O `.pbix` é um binário de dezenas de MB que não se revisa em PR.
No PBIP, cada medida, relação e regra de segurança é uma linha de texto com diff.
É o formato usado com controle de versão e CI de Power BI.

**Fora do Git** (`.gitignore`): `**/.pbi/localSettings.json`, `**/.pbi/cache.abf`
(o cache de dados importados) e `**/.pbi/editorSettings.json` se só guardar
preferência local. Consequência: quem abrir o projeto vê o modelo sem dados até
atualizar.

## 3. Fonte de dados

Postgres local, pelo conector nativo do Power BI, em modo **Import**.

Dois parâmetros do Power Query em `expressions.tmdl`:

| Parâmetro | Padrão |
|---|---|
| `ServidorPostgres` | `localhost:5432` |
| `BancoPostgres` | `olist` |

Cada tabela lê `marts.<tabela>` com esses parâmetros. Trocar para o Neon é mudar
o servidor e o banco. A credencial não fica no projeto: o Desktop pede usuário e
senha na primeira atualização (local: os valores de desenvolvimento do
`.env.example`).

**Por que Import.** Dashboard executivo sobre dado que muda uma vez por carga; o
VertiPaq responde em milissegundos. DirectQuery só se justificaria com dado que
muda a toda hora.

## 4. Modelo semântico

**Tabelas** (colunas só as usadas; chaves escondidas):

| Tabela | Grão | Papel |
|---|---|---|
| `fato_pedidos` | pedido | receita, entrega, nota |
| `fato_itens_pedido` | item | produto e vendedor |
| `dim_tempo` | dia | marcada como tabela de datas (coluna `data`) |
| `dim_clientes` | pessoa | região e UF do cliente |
| `dim_produtos` | produto | categoria e grupo |
| `dim_vendedores` | vendedor | UF e região do vendedor |
| `previsao_atraso` | pedido | probabilidade e alerta da Etapa 4 |
| `seguranca_bi` | usuário | quem vê o quê (oculta, sem relação) |

`dim_geolocalizacao` e as OBTs ficam de fora: nada das três páginas precisa
delas, e as OBTs existem só por causa do Looker.

**Relações** (um para muitos, filtro numa direção, da dimensão para o fato):

| De (um) | Para (muitos) | Chave |
|---|---|---|
| `dim_tempo` | `fato_pedidos`, `fato_itens_pedido` | `tempo_sk` = `tempo_sk_compra` |
| `dim_clientes` | `fato_pedidos`, `fato_itens_pedido` | `cliente_sk` |
| `dim_produtos` | `fato_itens_pedido` | `produto_sk` |
| `dim_vendedores` | `fato_itens_pedido` | `vendedor_sk` |
| `fato_pedidos` | `previsao_atraso` | `pedido_sk` |

A última é um para um no dado, modelada como um para muitos a partir do fato: o
filtro das dimensões chega à previsão passando pelo fato.

## 5. Medidas DAX

Ficam numa tabela de medidas (`_Medidas`), em pastas de exibição.

| Pasta | Medida | Definição |
|---|---|---|
| Vendas | Receita | `SUM(fato_pedidos[valor_total])` |
| Vendas | Pedidos | `DISTINCTCOUNT(fato_pedidos[order_id])` |
| Vendas | Ticket Médio | `DIVIDE([Receita], [Pedidos])` |
| Vendas | Clientes | `DISTINCTCOUNT(fato_pedidos[cliente_sk])` |
| Tempo | Receita Mês Anterior | `CALCULATE([Receita], DATEADD(dim_tempo[data], -1, MONTH))` |
| Tempo | Variação Mensal % | `DIVIDE([Receita] - [Receita Mês Anterior], [Receita Mês Anterior])` |
| Tempo | Receita Acumulada no Ano | `TOTALYTD([Receita], dim_tempo[data])` |
| Tempo | Receita Ano Anterior | `CALCULATE([Receita], SAMEPERIODLASTYEAR(dim_tempo[data]))` |
| Tempo | Variação Anual % | como a mensal, contra o ano anterior |
| Entrega | Entregues | pedidos com `entregue_no_prazo` não nulo |
| Entrega | Atrasos | pedidos com `entregue_no_prazo = FALSE` |
| Entrega | Taxa de Atraso | `DIVIDE([Atrasos], [Entregues])` |
| Entrega | % no Prazo | `1 - [Taxa de Atraso]`, nos entregues |
| Entrega | Taxa Nacional de Atraso | `CALCULATE([Taxa de Atraso], REMOVEFILTERS(dim_clientes))` |
| Entrega | Atraso em Excesso | `[Atrasos] - [Entregues] * [Taxa Nacional de Atraso]` |
| Satisfação | Nota Média | `AVERAGE(fato_pedidos[nota_avaliacao])` |
| Risco | Pedidos em Alerta | alertas da previsão em `conjunto` teste ou em andamento |
| Risco | Receita em Risco | receita dos pedidos em alerta, mesmo filtro |

**Regra das medidas de risco.** Só contam `teste` e `em_andamento`: previsões
sobre treino e validação são otimistas (docs/modelo-atraso.md).

**Interação com o RLS, registrada no README.** `REMOVEFILTERS` não atravessa o
RLS. Para um gerente regional, a "taxa nacional" vira a taxa da região dele, e o
atraso em excesso tende a zero. É o comportamento correto (ele não pode ver o
resto do país), e é um bom exemplo de por que medida comparativa precisa ser
pensada junto com a segurança.

## 6. Segurança

**Tabela de usuários.** Seed do dbt `dbt/seeds/seguranca_bi.csv`, materializada
em `marts.seguranca_bi`. Usuários fictícios em `@exemplo.com.br`:

| email | perfil | regiao | seller_id |
|---|---|---|---|
| diretoria@exemplo.com.br | Diretoria | | |
| gerente.nordeste@exemplo.com.br | Gerente regional | Nordeste | |
| gerente.sudeste@exemplo.com.br | Gerente regional | Sudeste | |
| vendedor.a@exemplo.com.br | Vendedor | | 6560211a19b47992c3666cc44a7e94c0 |
| vendedor.b@exemplo.com.br | Vendedor | | 4a3ca9315b744ce9f8e9374361493884 |
| vendedor.b@exemplo.com.br | Vendedor | | 1f50f920176fa81dab994f9023523100 |

Os vendedores são reais da base, escolhidos entre os de maior volume que também
existem na amostra do CI (o seed tem teste de relacionamento com
`dim_vendedores`). `vendedor.b` tem dois vendedores para mostrar um usuário com
mais de uma conta.

**Papéis (RLS dinâmico, por `USERPRINCIPALNAME()`):**

| Papel | Filtro |
|---|---|
| Diretoria | nenhum (`TRUE()`) |
| Gerente regional | `dim_clientes[regiao]` nas regiões do usuário |
| Vendedor | `dim_vendedores[seller_id]` nos vendedores do usuário; `fato_pedidos[order_id]` nos pedidos que têm item desses vendedores |

Nos três, `seguranca_bi` fica filtrada para a linha do próprio usuário.

**Por que dinâmico.** Um papel por região não escala (cinco regiões, cinco papéis,
e o mesmo para cada vendedor). Com a tabela, incluir alguém é uma linha nova, e
quem administra acesso não precisa mexer no modelo.

**OLS.** No papel Vendedor, `dim_clientes[customer_unique_id]`,
`dim_clientes[zip_code_prefix]` e `dim_clientes[cidade]` ficam com permissão
`None`. É a leitura de LGPD: o vendedor vê quanto vendeu e para qual UF, não quem
comprou.

**Limite registrado.** No papel Vendedor, a receita de um pedido com itens de
mais de um vendedor aparece inteira nas medidas de `fato_pedidos` (cerca de 2%
dos pedidos). As medidas de item (`fato_itens_pedido`) são as exatas para ele, e a
página Vendedores usa essas.

**Teste.** "Exibir como" com o papel e "Outro usuário" igual ao e-mail. Cada
perfil tem um número esperado vindo do SQL (seção 9).

## 7. Páginas

Tema próprio em JSON, nas cores do dashboard do Looker (`#0F52BA`, `#60A5FA`,
`#F1F5F9`, `#475569`), para os dois relatórios parecerem do mesmo projeto.

1. **Executivo.**
   - Cartões: receita, pedidos, ticket médio, % no prazo e nota média, cada um com
     a variação mensal.
   - Linha de receita por mês, com o ano anterior.
   - Segmentação de período e de região.
2. **Entrega e risco.**
   - Taxa de atraso por região contra a taxa nacional.
   - Atraso em excesso por UF, em barras ordenadas: o RJ deve aparecer no topo.
   - Pedidos em andamento ordenados por probabilidade de atraso.
   - Cartões de pedidos em alerta e receita em risco.
3. **Vendedores** (grão de item).
   - Receita de itens por vendedor e por grupo de categoria.
   - Taxa de atraso dos pedidos de cada vendedor.
   - É a página que o perfil Vendedor usa.

## 8. Como é construído

- O modelo (tabelas, relações, medidas, papéis, OLS) é escrito direto em TMDL.
- O relatório é escrito em PBIR. Se algum visual não for aceito pelo Desktop do
  jeito escrito, ele é montado na interface e salvo: o PBIP grava o PBIR do mesmo
  jeito, e o resultado continua versionado.
- A abertura, a atualização, a conferência e os prints são feitos no Power BI
  Desktop desta máquina, com controle da tela. Se o Desktop pedir para ativar os
  recursos de PBIP/TMDL/PBIR nas opções de versão prévia, isso é feito antes.

## 9. Conferência

**Números do modelo contra o SQL** (dataset inteiro, sem filtro):

| Medida | Esperado |
|---|---|
| Pedidos | 99.441 |
| Receita | R$ 15.843.553,24 |
| Ticket Médio | R$ 159,33 |
| % no Prazo | 93,2% (base: entregues) |
| Nota Média | 4,09 |
| Atraso em Excesso, RJ | cerca de +659 (Etapa 2) |

O atraso em excesso do RJ será recalculado em SQL com a mesma definição da
medida antes da conferência; a análise da Etapa 2 usou janela e base próprias, e
pequenas diferenças precisam ser explicadas, não ajustadas.

**Segurança contra o SQL:** para cada usuário do seed, pedidos e itens visíveis
calculados por consulta e comparados com o "Exibir como".

## 10. Riscos

- **Recursos de versão prévia.** PBIP, TMDL e PBIR podem exigir ativação nas
  opções do Desktop desta versão; o Desktop da loja se atualiza sozinho e pode
  mudar o formato. A versão usada fica registrada no README.
- **PBIR escrito à mão.** O esquema dos visuais é detalhado; erros aparecem só ao
  abrir. Mitigação: começar por um visual, abrir, ajustar, e então seguir.
- **RLS mal configurado vaza dado.** Mitigação: teste por usuário contra SQL, não
  só olhando o visual.
- **Cache fora do Git.** Quem clonar vê o relatório vazio até atualizar; o
  README diz isso.

## 11. Fora do escopo

- Publicação no Power BI Service, workspace e testes de RLS com usuários reais.
- Atualização incremental, pipelines de implantação e agregações.
- Grupo de cálculo de inteligência de tempo (as medidas explícitas bastam para as
  três páginas; fica como próxima melhoria).
