# Dashboards

## Arquitetura de servico do BI

```
data/raw (CSVs)  ->  Postgres local (Docker)  ->  dbt build (91 nos, 70 testes)
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

## Paginas sugeridas

**1. Visao geral** (fonte: `obt_pedidos`)
- Scorecards: `COUNT(order_id)`, `SUM(valor_total)`, `AVG(valor_total)`,
  `AVG(nota_avaliacao)`.
- Serie temporal: `ano_mes_compra` no eixo X, `SUM(valor_total)` no Y.
- Filtro de periodo por `data_compra`, aplicado ao relatorio inteiro.

**2. Geografia** (fonte: `obt_pedidos`)
- Mapa de bolhas usando `cliente_latlong`, tamanho por `SUM(valor_total)`.
- Barras: `cliente_regiao` por receita.
- Tabela: top 15 `cliente_cidade` com receita e ticket medio.

**3. Entregas** (fonte: `obt_pedidos`)
- Scorecard de `entregue_no_prazo` como percentual, **com filtro `foi_entregue = true`** na pagina (veja a nota sobre denominador abaixo).
- Barras: `AVG(tempo_entrega_dias)` por `cliente_regiao`, mesmo filtro.
- Histograma de `atraso_dias` filtrando `foi_entregue = true`.

**4. Produtos e vendedores** (fonte: `obt_itens`)
- Barras: top 15 `categoria_pt` por `SUM(valor_item)`.
- Tabela: top 20 `seller_id` com receita, itens vendidos e ticket medio.
- Segmentacao por `venda_interregional` para mostrar o efeito no frete.

**5. Satisfacao** (fonte: `obt_pedidos`)
- `AVG(nota_avaliacao)` por `cliente_regiao` e por faixa de `atraso_dias`.
- Essa cruzada e a mais interessante do dataset: a nota cai junto com o atraso.

---

## Numeros de conferencia

Se o dashboard mostrar valores diferentes destes, algo esta errado no filtro ou
na fonte de dados:

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
