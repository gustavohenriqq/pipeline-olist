# Dashboards

## Arquitetura de servico do BI

```
data/raw (CSVs)  ->  Postgres local (Docker)  ->  dbt build (95 nos, 74 testes)
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
                                              Looker Studio (publico)
```

**Por que o Neon existe neste desenho.** O Looker Studio precisa alcancar o
banco pela internet. Um Postgres em `localhost` so responde enquanto a sua
maquina esta ligada e exposta, o que nao serve para um dashboard de portfolio
que alguem vai abrir semanas depois. O Neon e um Postgres serverless gratuito
que resolve isso.

**Por que so as marts sobem.** O free tier do Neon da 0,5 GB. So a tabela crua
`geolocation` tem 1 milhao de linhas (58 MB em CSV). Publicando apenas a camada
de marts, o banco na nuvem ocupa **147 MB, cerca de 29% do limite**, com folga
para crescer. Esse tambem e o desenho correto em producao: ferramenta de BI
nunca le a camada crua, le o modelo ja testado.

**Por que o dbt nao roda direto no Neon.** Rodaria, e o `dbt/profiles.yml` tem o
target `prod` documentado para isso. Mas o staging le de `raw`, entao a camada
crua inteira teria que morar la, e cada `dbt build` viraria trafego de rede.
Construir local e publicar so o resultado testado e mais rapido e mais barato.

---

## Passo a passo: publicar no Neon

Ja feito uma vez. Para atualizar depois de mudar um model:

```bash
# 1. Reconstruir e testar local (nada vai para a nuvem sem passar nos testes)
cd dbt && dbt build --profiles-dir . && cd ..

# 2. Espelhar as marts no Neon
python scripts/publicar_marts.py

# ou uma tabela so
python scripts/publicar_marts.py obt_pedidos
```

No Windows, com o ambiente virtual do projeto, troque `python` por
`.venv\Scripts\python.exe` e `dbt` por `.venv\Scripts\python.exe -m dbt.cli.main`.

O script recria cada tabela do zero (DROP + CREATE + COPY) dentro de uma
transacao. Se qualquer tabela falhar, nada e commitado e o Neon fica como
estava. Carga full e proposital: as marts sao reconstruidas inteiras pelo dbt a
cada run, entao publicacao incremental so traria risco de divergencia
silenciosa entre os dois bancos.

---

## Passo a passo: conectar o Looker Studio

1. Abra https://lookerstudio.google.com e clique em **Criar -> Fonte de dados**.
2. Escolha o conector **PostgreSQL**.
3. Preencha com os dados do seu `.env` (bloco `NEON_*`):

   | Campo | Valor |
   |---|---|
   | Host | o valor de `NEON_HOST` |
   | Port | deixe em branco (o conector usa a porta padrao) |
   | Database | `neondb` |
   | Username | `neondb_owner` |
   | Password | o valor de `NEON_PASSWORD` |

4. **Marque "Enable SSL"**. O Neon so aceita conexao criptografada; sem essa
   marcacao a conexao e recusada. Ao marcar, aparecem campos novos:
   - **Server certificate:** baixe o certificado raiz da Let's Encrypt em
     https://letsencrypt.org/certs/isrgrootx1.pem e faca upload dele.
   - **Enable client authentication:** deixe **desmarcado**.

   Use o host **com** `-pooler` no nome, que e o que o guia oficial do Neon
   indica para o Looker Studio: https://neon.com/docs/connect/connect-looker-studio

   > Correcao: uma versao anterior deste guia mandava deixar os campos de
   > certificado em branco. O guia oficial do Neon pede o upload do certificado.

   **Se for trocar a senha do Neon, troque antes de conectar.** Senha trocada
   depois derruba todas as fontes de dados do relatorio, e cada uma precisa ser
   autenticada de novo.
5. Clique em **Autenticar** e depois escolha a aba **CUSTOM QUERY**.

   Use custom query em vez de selecionar a tabela na lista: o conector do Looker
   nem sempre enxerga schemas fora do `public`, e a query deixa explicito de
   onde o dado vem.

   Para as paginas de receita, entrega e satisfacao:
   ```sql
   SELECT * FROM marts.obt_pedidos
   ```

   Crie uma **segunda fonte de dados**, repetindo os passos, para as paginas de
   categoria e vendedor:
   ```sql
   SELECT * FROM marts.obt_itens
   ```

6. Em **Conectar**, confira os tipos: `data_compra` deve estar como Data,
   `valor_total` como Numero, `cliente_latlong` como **Latitude, Longitude**
   (o Looker as vezes marca como texto; corrija na lista de campos).

### Por que duas fontes, e nunca uma so

`obt_pedidos` esta no grao de **pedido**; `obt_itens`, no grao de **item**. Um
pedido tem varios itens. Se voce somar `valor_total` (metrica de pedido) numa
visao que veio do grao de item, cada pedido e contado uma vez por item e a
receita infla. Mantenha cada pagina ligada a uma fonte so:

| Pergunta | Fonte |
|---|---|
| Receita, ticket medio, pedidos, entrega, nota | `obt_pedidos` |
| Categoria de produto, performance de vendedor, frete por item | `obt_itens` |

---

## Pagina 1: Visao Geral Comercial

Estado em 02/10/2026: **em montagem no Looker Studio, ainda nao publicada.**
Cards, evolucao de vendas e taxa de atraso por regiao estao prontos e
conferidos contra o banco. Categorias, notas e mapa estao sendo ajustados.

### Configuracao geral

| Ajuste | Valor |
|---|---|
| Tamanho da tela | Personalizado, 1600 x 900 |
| Controle de periodo | **Fixo**, 01/01/2017 a 31/08/2018, no nivel do relatorio |
| Tema, "Cor de acordo com" | Valores de dimensao |
| Fundo da pagina / cards | `#F1F5F9` / `#FFFFFF`, borda `#E2E8F0` |
| Cor principal | `#0F52BA` (linhas), `#60A5FA` (barras em destaque) |
| Contexto e referencia | `#CBD5E1` (barras), `#94A3B8` (linhas de referencia) |

**Por que o periodo comeca em jan/2017.** O dataset cobre set/2016 a out/2018,
mas as pontas sao residuo de coleta: 349 pedidos, 0,35% do total. Plotar o
periodo inteiro achata a serie contra o eixo. O controle continua livre para
quem abrir o relatorio; o padrao fixo so define a primeira impressao.

### Filtros do cabecalho

| Filtro | Controle | Fonte | Campo |
|---|---|---|---|
| Periodo | Controle de periodo | (todas) | dimensao de periodo de cada grafico |
| Status do pedido | Lista suspensa | `obt_pedidos` | `status_pedido` |
| Regiao | Lista suspensa | `obt_pedidos` | `cliente_regiao` |
| Categoria | Lista suspensa | `obt_itens` | `categoria_grupo` |

O filtro de status nao afeta graficos da `obt_itens`, que nao tem esse campo. O
de regiao funciona nas duas fontes porque o campo tem o mesmo nome nelas.

### Os cinco cards (todos da `obt_pedidos`)

| Card | Metrica | Agregacao | Filtro | Formato |
|---|---|---|---|---|
| Pedidos | `order_id` | Contagem distinta | nenhum | Numero, 0 casas |
| Receita bruta | `valor_total` | Soma | nenhum | Moeda BRL, compacto, 2 casas |
| Clientes unicos | `customer_unique_id` | **Contagem distinta** | nenhum | Numero, 0 casas |
| Entregue no prazo | `no_prazo_num` | Media | **`foi_entregue` = true** | Percentual, 1 casa |
| Avaliacao media | `nota_avaliacao` | Media | nenhum | Numero, 2 casas |

Em todos: dimensao do periodo `data_compra`, periodo padrao Automatico,
comparacao desligada.

**Por que os cards nao tem variacao contra periodo anterior.** Com a janela de 20
meses, "periodo anterior" sao os 20 meses antes de jan/2017, que tem 329 pedidos.
O card mostraria **+27.506%**. "Ano anterior" mostraria +330%, com metade da base
fora do dataset. O crescimento real esta contado no grafico de evolucao.

### Graficos

| Grafico | Fonte | Configuracao |
|---|---|---|
| **Evolucao de vendas** | `obt_pedidos` | Serie temporal, `data_compra` em **Ano e mes**, `valor_total` Soma. Area em gradiente, linha de referencia constante 789310 (media mensal), anotacao da Black Friday em caixa de texto |
| **Taxa de atraso por regiao** | `obt_pedidos` | Barras horizontais, `cliente_regiao`, `atrasou` Media, filtro so entregues. Linha de referencia **0.068**. Formatacao condicional: `atrasou` > 0.068 em `#60A5FA`, resto em `#E2E8F0` |
| **Top categorias** | `obt_itens` | Barras horizontais, `categoria_grupo`, `valor_item` Soma, 5 linhas, sem "Outros" |
| **Distribuicao das notas** | `obt_pedidos` | Colunas, `nota_avaliacao` ordenada **pela dimensao**, `order_id` Contagem distinta, excluir nota nula. Notas 1 a 3 em `#CBD5E1`, 4 e 5 em `#60A5FA` (clientes satisfeitos) |
| **Mapa por estado** | `obt_pedidos` | Mapa geografico, `uf_iso`, `valor_total` Soma, com cor minima, **media** e maxima |

### Campos calculados criados no Looker (fonte `obt_pedidos`)

| Campo | Formula | Uso |
|---|---|---|
| `no_prazo_num` | `CASE WHEN entregue_no_prazo = TRUE THEN 1 WHEN entregue_no_prazo = FALSE THEN 0 END` | Card de entregue no prazo |
| `atrasou` | `CASE WHEN entregue_no_prazo = FALSE THEN 1 WHEN entregue_no_prazo = TRUE THEN 0 END` | Taxa de atraso. Tipo Percentual |
| `uf_iso` | `CONCAT("BR-", cliente_uf)` | Mapa. Tipo Geo, subdivisao do pais (1o nivel) |

Os dois `CASE` nao tem `ELSE` de proposito. Com `ELSE 0`, o pedido sem data de
entrega entraria na media como atrasado, e o card cairia de 93,2% para 90,5%.

---

## Armadilhas do Looker Studio pagas na montagem

Registradas porque cada uma custou uma rodada de tentativa e erro:

- **Card mostrando o dataset inteiro (99.441) com o filtro de periodo ativo.** Duas
  causas possiveis: o grafico sem **Dimensao do periodo** definida (obrigatoria
  quando a fonte tem mais de uma data) ou o controle de periodo sem padrao, que
  equivale a "todas as datas".
- **Numero compacto nao fica no formato do campo.** "R$ 15,79 mi" se liga na aba
  **Estilo** do card. O formato do campo so define tipo e casas.
- **Linha de referencia usa o valor bruto.** Metrica percentual em media de 0 e 1
  pede `0.068`, nao `6.8`.
- **O rotulo da linha de referencia herda a cor da linha** e nao tem controle
  proprio. Para cor diferente, desligar o rotulo e usar caixa de texto.
- **Cor barra a barra.** Cor por valor de dimensao so funciona com uma serie por
  valor. A saida limpa e **formatacao condicional pela metrica**, que ainda
  acompanha os filtros: uma regra "acima da media" muda sozinha quando o recorte
  muda, enquanto cor fixa por regiao mentiria.
- **Escala ordinal ordenada pela metrica.** As notas sairam como 5, 4, 1, 3, 2.
  Escala se ordena pela propria dimensao.
- **Rosca com 97% numa fatia nao informa.** Motivou o campo `situacao_pedido` no
  dbt (Entregue, Em andamento, Nao concluido).
- **Mapa de receita com SP dominante.** SP tem 37% da receita e 20 estados tem
  menos de 10% do que SP fatura. Sem cor media na escala, os 20 ficam no mesmo
  tom.

---

## Numeros de conferencia

Se o dashboard mostrar valores diferentes destes, algo esta errado no filtro ou
na fonte de dados.

### Na janela padrao do relatorio (01/01/2017 a 31/08/2018)

| Metrica | Valor esperado |
|---|---|
| Pedidos | 99.092 |
| Receita bruta | R$ 15,79 mi |
| Clientes unicos | 95.774 |
| Entregue no prazo | 93,2% (base: entregues) |
| Avaliacao media | 4,09 |
| Taxa de atraso nacional | 6,8% |
| Nordeste / Sudeste (taxa de atraso) | 12,7% / 6,1% |
| Top categoria | Casa e Decoracao, R$ 3,23 mi |
| SP no mapa | R$ 5,91 mi |
| Pico de receita | nov/2017, R$ 1,18 mi |

### No dataset inteiro (set/2016 a out/2018)

| Metrica | Valor esperado | Denominador |
|---|---|---|
| Pedidos | 99.441 | todos |
| Receita total | R$ 15.843.553,24 | todos |
| Ticket medio | R$ 159,33 | todos |
| Tempo medio de entrega | 12,5 dias | so os entregues |
| Entregue no prazo | 93,2% | so os entregues |
| Nota media | 4,09 | pedidos com avaliacao |
| Periodo coberto | 04/09/2016 a 17/10/2018 | todos |

**Cuidado com o denominador do "no prazo".** 2.965 pedidos ainda estao em
transito ou foram cancelados, e para eles `entregue_no_prazo` e nulo. Se voce
somar esses pedidos ao denominador, o indicador cai para 90,4% e voce estara
contando como atrasado um pedido que ainda nem venceu o prazo. No Looker, filtre
`foi_entregue = true` antes de calcular esse percentual. O mesmo vale para
`tempo_entrega_dias` e `atraso_dias`.

---

## Detalhes do Neon que podem confundir

- **A primeira consulta demora.** O free tier suspende a computacao depois de
  alguns minutos parada. A proxima query religa (cold start de menos de um
  segundo). Nao e erro de conexao.
- **Cache do Looker.** O Looker guarda resultado em cache. Depois de republicar,
  use **Atualizar dados** no relatorio para ver o dado novo.
- **A senha esta no `.env`, que nao vai para o Git.** Se precisar troca-la,
  gere outra no painel do Neon (Roles -> Reset password) e atualize o `.env`.

Link do dashboard publicado: _a preencher depois de publicar._

## Power BI (Fase 4)

- Conectar via Import ao Postgres/Azure SQL.
- Diferente do Looker, o Power BI trabalha bem com star schema: ligue
  `fato_pedidos` e `fato_itens_pedido` as dimensoes pelas chaves `_sk` e ignore
  as OBTs. O motor VertiPaq foi feito para modelo dimensional.
- Medidas DAX, RLS por regiao/vendedor e OLS para metricas sensiveis.

Os arquivos `.pbix` e os prints ficam nesta pasta e em `docs/prints/`.
