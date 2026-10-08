# Dashboards

## Arquitetura de serviço do BI

```
data/raw (CSVs)  ->  Postgres local (Docker)  ->  dbt build (95 nós, 74 testes)
                                                        |
                                                        v
                                              marts (star schema + OBTs)
                                                        |
                                            scripts/publicar_marts.py
                                                        |
                                                        v
                                      Neon (Postgres serverless, gratuito)
                                                        |
                                                        v
                                              Looker Studio (público)
```

**Por que o Neon existe neste desenho.** O Looker Studio precisa alcançar o
banco pela internet. Um Postgres em `localhost` só responde enquanto a sua
máquina está ligada e exposta, o que não serve para um dashboard de portfólio
que alguém vai abrir semanas depois. O Neon é um Postgres serverless gratuito
que resolve isso.

**Por que só as marts sobem.** O free tier do Neon dá 0,5 GB. Só a tabela crua
`geolocation` tem 1 milhão de linhas (58 MB em CSV). Publicando apenas a camada
de marts, o banco na nuvem ocupa **147 MB, cerca de 29% do limite**, com folga
para crescer. Esse também é o desenho correto em produção: ferramenta de BI
nunca lê a camada crua, lê o modelo já testado.

**Por que o dbt não roda direto no Neon.** Rodaria, e o `dbt/profiles.yml` tem o
target `prod` documentado para isso. Mas o staging lê de `raw`, então a camada
crua inteira teria que morar lá, e cada `dbt build` viraria tráfego de rede.
Construir local e publicar só o resultado testado é mais rápido e mais barato.

---

## Passo a passo: publicar no Neon

Já feito uma vez. Para atualizar depois de mudar um model:

```bash
# 1. Reconstruir e testar local (nada vai para a nuvem sem passar nos testes)
cd dbt && dbt build --profiles-dir . && cd ..

# 2. Espelhar as marts no Neon
python scripts/publicar_marts.py

# ou uma tabela só
python scripts/publicar_marts.py obt_pedidos
```

No Windows, com o ambiente virtual do projeto, troque `python` por
`.venv\Scripts\python.exe` e `dbt` por `.venv\Scripts\python.exe -m dbt.cli.main`.

O script recria cada tabela do zero (DROP + CREATE + COPY) dentro de uma
transação. Se qualquer tabela falhar, nada é commitado e o Neon fica como
estava. Carga full é proposital: as marts são reconstruídas inteiras pelo dbt a
cada run, então publicação incremental só traria risco de divergência
silenciosa entre os dois bancos.

---

## Passo a passo: conectar o Looker Studio

1. Abra https://lookerstudio.google.com e clique em **Criar -> Fonte de dados**.
2. Escolha o conector **PostgreSQL**.
3. Preencha com os dados do seu `.env` (bloco `NEON_*`):

   | Campo | Valor |
   |---|---|
   | Host | o valor de `NEON_HOST` |
   | Port | deixe em branco (o conector usa a porta padrão) |
   | Database | `neondb` |
   | Username | `neondb_owner` |
   | Password | o valor de `NEON_PASSWORD` |

4. **Marque "Enable SSL"**. O Neon só aceita conexão criptografada; sem essa
   marcação a conexão é recusada. Ao marcar, aparecem campos novos:
   - **Server certificate:** baixe o certificado raiz da Let's Encrypt em
     https://letsencrypt.org/certs/isrgrootx1.pem e faça upload dele.
   - **Enable client authentication:** deixe **desmarcado**.

   Use o host **com** `-pooler` no nome, que é o que o guia oficial do Neon
   indica para o Looker Studio: https://neon.com/docs/connect/connect-looker-studio

   > Correção: uma versão anterior deste guia mandava deixar os campos de
   > certificado em branco. O guia oficial do Neon pede o upload do certificado.

   **Se for trocar a senha do Neon, troque antes de conectar.** Senha trocada
   depois derruba todas as fontes de dados do relatório, e cada uma precisa ser
   autenticada de novo.
5. Clique em **Autenticar** e depois escolha a aba **CUSTOM QUERY**.

   Use custom query em vez de selecionar a tabela na lista: o conector do Looker
   nem sempre enxerga schemas fora do `public`, e a query deixa explícito de
   onde o dado vem.

   Para as páginas de receita, entrega e satisfação:
   ```sql
   SELECT * FROM marts.obt_pedidos
   ```

   Crie uma **segunda fonte de dados**, repetindo os passos, para as páginas de
   categoria e vendedor:
   ```sql
   SELECT * FROM marts.obt_itens
   ```

   E uma **terceira**, para o rodapé, com atualização dos dados a cada hora (o
   padrão de 12 horas mostraria uma data velha por meio dia depois de publicar):
   ```sql
   SELECT * FROM marts.atualizacao_dados
   ```
   Nela, `processado_em`, `carga_raw_em` e `resumo` ficam como **Texto** (ver as
   armadilhas abaixo).

6. Em **Conectar**, confira os tipos: `data_compra` deve estar como Data,
   `valor_total` como Número, `cliente_latlong` como **Latitude, Longitude**
   (o Looker às vezes marca como texto; corrija na lista de campos).

### Por que duas fontes, e nunca uma só

`obt_pedidos` está no grão de **pedido**; `obt_itens`, no grão de **item**. Um
pedido tem vários itens. Se você somar `valor_total` (métrica de pedido) numa
visão que veio do grão de item, cada pedido é contado uma vez por item e a
receita infla. Mantenha cada página ligada a uma fonte só:

| Pergunta | Fonte |
|---|---|
| Receita, ticket médio, pedidos, entrega, nota | `obt_pedidos` |
| Categoria de produto, performance de vendedor, frete por item | `obt_itens` |

---

## Página 1: Visão Geral Comercial

Estado em 08/10/2026: **publicada**, com acesso "não listado" (qualquer pessoa
com o link vê, ninguém além do dono edita):
**[https://datastudio.google.com/reporting/f66379d8-5fd9-4d0c-8e9c-4cd7019db7c7](https://datastudio.google.com/reporting/f66379d8-5fd9-4d0c-8e9c-4cd7019db7c7)**

Todos os componentes foram conferidos contra o banco. O link foi testado num
navegador sem login Google, e os números carregaram.

![Visão Geral Comercial](../docs/prints/visao-geral-comercial.png)

**Rodapé do relatório.** A página tem 1600 x 965 (65 px a mais que o padrão 16:9)
para caber duas linhas:

- o aviso "Dados públicos da Olist (Kaggle) [...] Projeto independente de
  portfólio, sem vínculo com a Olist". O logo da Olist no cabeçalho sem esse
  aviso faria o relatório parecer material oficial da empresa;
- a linha de atualização, por exemplo "Dados processados em 08/10/2026 18:26
  (Brasília) · 81 testes ok, 3 avisos", lida de `marts.atualizacao_dados`. Ela é
  reescrita a cada `dbt build` completo (sem `--select`) e chega ao Neon com as outras marts (ver
  [docs/confiabilidade.md](../docs/confiabilidade.md)).

### Configuração geral

| Ajuste | Valor |
|---|---|
| Tamanho da tela | Personalizado, 1600 x 965 (na página; o tema do relatório segue 1600 x 900) |
| Controle de período | **Fixo**, 01/01/2017 a 31/08/2018, no nível do relatório |
| Tema, "Cor de acordo com" | Valores de dimensão |
| Fundo da página / cards | `#F1F5F9` / `#FFFFFF`, borda `#E2E8F0` |
| Cor principal | `#0F52BA` (linhas), `#60A5FA` (barras em destaque) |
| Contexto e referência | `#CBD5E1` (barras), `#94A3B8` (linhas de referência) |

**Por que o período começa em jan/2017.** O dataset cobre set/2016 a out/2018,
mas as pontas são resíduo de coleta: 349 pedidos, 0,35% do total. Plotar o
período inteiro achata a série contra o eixo. O controle continua livre para
quem abrir o relatório; o padrão fixo só define a primeira impressão.

### Filtros do cabeçalho

| Filtro | Controle | Fonte | Campo |
|---|---|---|---|
| Período | Controle de período | (todas) | dimensão de período de cada gráfico |
| Status | Lista suspensa | `obt_pedidos` | `status_pedido` (nome de exibição "Status"; "Status do pedido" ficava cortado) |
| Região | Lista suspensa | `obt_pedidos` | `cliente_regiao` |
| Categoria | Lista suspensa | `obt_itens` | `categoria_grupo` |

O filtro de status não afeta gráficos da `obt_itens`, que não tem esse campo. O
de região funciona nas duas fontes porque o campo tem o mesmo nome nelas.

### Os cinco cards (todos da `obt_pedidos`)

| Card | Métrica | Agregação | Filtro | Formato |
|---|---|---|---|---|
| Pedidos | `order_id` | Contagem distinta | nenhum | Número, 0 casas |
| Receita bruta | `valor_total` | Soma | nenhum | Moeda BRL, compacto, 2 casas |
| Clientes únicos | `customer_unique_id` | **Contagem distinta** | nenhum | Número, 0 casas |
| Entregue no prazo | `no_prazo_num` | Média | **`foi_entregue` = true** | Percentual, 1 casa |
| Avaliação média | `nota_avaliacao` | Média | nenhum | Número, 2 casas |

Em todos: dimensão do período `data_compra`, período padrão Automático,
comparação desligada.

**Por que os cards não têm variação contra período anterior.** Com a janela de 20
meses, "período anterior" são os 20 meses antes de jan/2017, que têm 329 pedidos.
O card mostraria **+27.506%**. "Ano anterior" mostraria +330%, com metade da base
fora do dataset. O crescimento real está contado no gráfico de evolução.

### Gráficos

| Gráfico | Fonte | Configuração |
|---|---|---|
| **Evolução de vendas** | `obt_pedidos` | Série temporal, `data_compra` em **Ano e mês**, `valor_total` Soma. Área em gradiente, linha de referência constante 789310 (média mensal), anotação da Black Friday em caixa de texto |
| **Taxa de atraso por região** | `obt_pedidos` | Barras horizontais, `cliente_regiao`, `atrasou` Média, filtro só entregues. Linha de referência **0.068**. Formatação condicional: `atrasou` > 0.068 em `#60A5FA`, resto em `#E2E8F0` |
| **Receita por categoria** | `obt_itens` | Barras horizontais, `categoria_grupo`, `valor_item` Soma em BRL, **10 grupos sem "Outros"**, barras `#60A5FA`. Rótulos compactos com 2 casas (R$ 1,03 mi e R$ 1,02 mi deixam de parecer iguais). Eixo X sem rótulos e com máximo fixo em **4.000.000**, para o rótulo da maior barra caber fora dela |
| **Distribuição das notas** | `obt_pedidos` | Barras, `nota_avaliacao` ordenada **pela dimensão**, `order_id` Contagem distinta (nome **"Pedidos avaliados"**), excluir nota nula. Notas 1 a 3 em `#CBD5E1`, 4 e 5 em `#60A5FA`. Eixo com máximo fixo em **70.000** pelo mesmo motivo |
| **Receita por estado (mapa)** | `obt_pedidos` | Gráfico de mapa, `uf_iso`, `valor_total` Soma em BRL, área Brasil, **sem legenda**. Cores: mínima `#E0ECFE`, média `#1D4ED8`, máxima `#0B1F5C` |
| **Linha de atualização (rodapé)** | `atualizacao_dados` | Tabela, dimensão `resumo`, sem métrica, sem dimensão de período, 1 linha (N principais). Sem cabeçalho, sem número de linha, fundo e bordas transparentes, Roboto 14px `#475569` (igual ao aviso) |
| **Resumo ao lado do mapa** | `obt_pedidos` | Tabela, `cliente_uf` ("UF"), `valor_total` ("Receita", compacta) e `valor_total` com cálculo **Porcentagem do total** ("%"). 5 primeiras linhas, sem numeração, sem borda |

**Nomes de exibição.** O tooltip do Looker mostra o nome do campo. Cada métrica e
dimensão foi renomeada no próprio gráfico ("Receita", "Taxa de atraso", "Nota",
"Estado"), sem mexer na fonte, para os nomes da fonte continuarem batendo com o
dbt. A métrica do gráfico de notas se chamava "Clientes", mas conta `order_id`:
o rótulo estava errado, não só feio.

**Os máximos fixos de eixo são seguros com qualquer filtro.** Nenhum grupo de
categoria passa de R$ 3,24 mi e nenhuma nota passa de 57 mil pedidos nem no
período completo.

**Os cinco cards estão agrupados** (fundo, ícone, título e valor de cada um) e
distribuídos para ocupar a mesma largura dos gráficos. Para editar uma peça,
duplo clique dentro do grupo ou Ctrl+Shift+G.

### Campos calculados criados no Looker (fonte `obt_pedidos`)

| Campo | Fórmula | Uso |
|---|---|---|
| `no_prazo_num` | `CASE WHEN entregue_no_prazo = TRUE THEN 1 WHEN entregue_no_prazo = FALSE THEN 0 END` | Card de entregue no prazo |
| `atrasou` | `CASE WHEN entregue_no_prazo = FALSE THEN 1 WHEN entregue_no_prazo = TRUE THEN 0 END` | Taxa de atraso. Tipo Percentual |
| `uf_iso` | `CONCAT("BR-", cliente_uf)` | Mapa. Tipo Geo, subdivisão do país (1o nível) |

Os dois `CASE` não têm `ELSE` de propósito. Com `ELSE 0`, o pedido sem data de
entrega entraria na média como atrasado, e o card cairia de 93,2% para 90,5%.

---

## Armadilhas do Looker Studio pagas na montagem

Registradas porque cada uma custou uma rodada de tentativa e erro:

- **Card mostrando o dataset inteiro (99.441) com o filtro de período ativo.** Duas
  causas possíveis: o gráfico sem **Dimensão do período** definida (obrigatória
  quando a fonte tem mais de uma data) ou o controle de período sem padrão, que
  equivale a "todas as datas".
- **Número compacto não fica no formato do campo.** "R$ 15,79 mi" se liga na aba
  **Estilo** do card. O formato do campo só define tipo e casas.
- **Linha de referência usa o valor bruto.** Métrica percentual em média de 0 e 1
  pede `0.068`, não `6.8`.
- **O rótulo da linha de referência herda a cor da linha** e não tem controle
  próprio. Para cor diferente, desligar o rótulo e usar caixa de texto.
- **Cor por valor de dimensão é chaveada pelo texto do valor.** Quando os rótulos
  do dbt ganharam acento ("Casa e Decoracao" virou "Casa e Decoração"), as cores
  atribuídas no Looker se perderam e precisaram ser refeitas. Renomear um rótulo no
  dbt é mudança que quebra o BI, mesmo sem mudar nenhum número.
- **Cor barra a barra.** Cor por valor de dimensão só funciona com uma série por
  valor. A saída limpa é **formatação condicional pela métrica**, que ainda
  acompanha os filtros: uma regra "acima da média" muda sozinha quando o recorte
  muda, enquanto cor fixa por região mentiria.
- **Escala ordinal ordenada pela métrica.** As notas saíram como 5, 4, 1, 3, 2.
  Escala se ordena pela própria dimensão.
- **Rosca com 97% numa fatia não informa.** Motivou o campo `situacao_pedido` no
  dbt (Entregue, Em andamento, Não concluído).
- **O mapa colore em escala linear entre o menor e o maior valor.** Com SP em
  37% da receita, quase todos os estados caem perto do mínimo e o mapa fica de
  uma cor só. A "cor média" fica no meio da escala (cerca de R$ 2,95 mi), então a
  saída é um mínimo quase branco e uma cor média forte: RJ e MG ficam em azul
  firme, Sul e BA em azul médio e o resto claro.
- **A legenda do mapa ignora o formato de moeda.** Mesmo com a métrica em BRL, ela
  mostra 5.906.209,11 sem R$. Foi escondida; a tabela ao lado traz os valores.
- **O valor no tooltip do mapa é o código ISO ("BR-SP").** É o valor do campo que
  o mapa exige, não o rótulo; por isso a tabela ao lado usa `cliente_uf`.
- **Título nativo do gráfico cai numa faixa fora do card** quando o fundo branco
  vem do próprio gráfico. Os títulos são caixas de texto por cima, 20 px negrito.
- **Forma retângulo não tem raio de borda**, então não serve de card para combinar
  com os gráficos arredondados.
- **Mover pelo teclado anda em saltos de cerca de 30 px** (ajuste a grade). Para
  alinhar, agrupar cada card e usar Organizar > Distribuir.
- **O controle de período fixo filtra qualquer fonte que tenha data.** A tabela
  do rodapé mostrava "Não há dados": o controle (2017 a 2018) filtrava a
  `atualizacao_dados` pela coluna `processado_em`, de 2026. Como essas datas são
  só registro, viraram Texto na fonte, e o gráfico ficou sem dimensão de período.
- **O Looker tipa como data um texto que começa com data.** O `resumo` ("Dados
  processados em 08/10/2026...") veio como Data e hora e precisou ser trocado
  para Texto.
- **Duplicar uma fonte (Recurso > Gerenciar fontes de dados > Duplicar) mantém
  as credenciais.** Assim dá para apontar a cópia para outra consulta sem digitar
  a senha do Neon de novo. A cópia nasce com o nome da original: renomeie antes
  de usar.

---

## Números de conferência

Se o dashboard mostrar valores diferentes destes, algo está errado no filtro ou
na fonte de dados.

### Na janela padrão do relatório (01/01/2017 a 31/08/2018)

| Métrica | Valor esperado |
|---|---|
| Pedidos | 99.092 |
| Receita bruta | R$ 15,79 mi |
| Clientes únicos | 95.774 |
| Entregue no prazo | 93,2% (base: entregues) |
| Avaliação média | 4,09 |
| Taxa de atraso nacional | 6,8% |
| Nordeste / Sudeste (taxa de atraso) | 12,7% / 6,1% |
| Top categoria | Casa e Decoração, R$ 3,23 mi |
| SP no mapa | R$ 5,91 mi |
| Pico de receita | nov/2017, R$ 1,18 mi |

### No dataset inteiro (set/2016 a out/2018)

| Métrica | Valor esperado | Denominador |
|---|---|---|
| Pedidos | 99.441 | todos |
| Receita total | R$ 15.843.553,24 | todos |
| Ticket médio | R$ 159,33 | todos |
| Tempo médio de entrega | 12,5 dias | só os entregues |
| Entregue no prazo | 93,2% | só os entregues |
| Nota média | 4,09 | pedidos com avaliação |
| Período coberto | 04/09/2016 a 17/10/2018 | todos |

**Cuidado com o denominador do "no prazo".** 2.965 pedidos ainda estão em
trânsito ou foram cancelados, e para eles `entregue_no_prazo` é nulo. Se você
somar esses pedidos ao denominador, o indicador cai para 90,4% e você estará
contando como atrasado um pedido que ainda nem venceu o prazo. No Looker, filtre
`foi_entregue = true` antes de calcular esse percentual. O mesmo vale para
`tempo_entrega_dias` e `atraso_dias`.

---

## Detalhes do Neon que podem confundir

- **A primeira consulta demora.** O free tier suspende a computação depois de
  alguns minutos parada. A próxima query religa (cold start de menos de um
  segundo). Não é erro de conexão.
- **Cache do Looker.** O Looker guarda resultado em cache. Depois de republicar,
  use **Atualizar dados** no relatório para ver o dado novo.
- **A senha está no `.env`, que não vai para o Git.** Se precisar trocá-la,
  gere outra no painel do Neon (Roles -> Reset password) e atualize o `.env`.

Link do dashboard publicado: **[https://datastudio.google.com/reporting/f66379d8-5fd9-4d0c-8e9c-4cd7019db7c7](https://datastudio.google.com/reporting/f66379d8-5fd9-4d0c-8e9c-4cd7019db7c7)**

## Power BI (Etapa 5)

- Conectar via Import ao Postgres/Azure SQL.
- Diferente do Looker, o Power BI trabalha bem com star schema: ligue
  `fato_pedidos` e `fato_itens_pedido` às dimensões pelas chaves `_sk` e ignore
  as OBTs. O motor VertiPaq foi feito para modelo dimensional.
- Medidas DAX, RLS por região/vendedor e OLS para métricas sensíveis.

Os arquivos `.pbix` e os prints ficam nesta pasta e em `docs/prints/`.
