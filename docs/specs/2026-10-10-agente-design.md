# Etapa 6: agente de IA sobre as marts (especificação)

Data: 10/10/2026. Branch: `feat/agente`.

## 1. Objetivo

Um agente que responde perguntas de negócio em português sobre as marts,
publicado num link público para quem visita o portfólio. A pergunta vira SQL, o
SQL roda num banco somente leitura, e a resposta mostra o número, a tabela, o SQL
gerado e, quando cabe, um gráfico.

O risco principal já está no ROADMAP: **resposta errada com cara de certa**. O
desenho inteiro gira em torno de três defesas: o SQL sempre visível, a resposta
escrita só a partir das linhas que o banco devolveu (com checagem automática dos
números) e uma avaliação com perguntas de resposta conhecida.

## 2. Decisões tomadas

| Tema | Decisão | Por quê |
|---|---|---|
| Onde roda | Streamlit Community Cloud (grátis), lendo o Neon | Link público para recrutador testar; o Neon já é a camada de serviço do BI |
| Modelo | Gemini Flash (camada gratuita) por padrão; Groq (Llama 3.3 70B, camada gratuita) como reserva quando a cota estoura | Restrição do dono: modelo gratuito. Os dois aceitam o formato da API da OpenAI, então um cliente só serve para ambos |
| Montagem | Pipeline próprio em Python, com passos explícitos | Cada passo é testável e as defesas ficam visíveis; agente pronto de framework decide sozinho quantas consultas faz e gasta a cota grátis |
| Escopo | Números das marts, com tabela e SQL; gráfico quando o usuário pede ou o resultado é série ou ranking | Testável contra o SQL, como a conferência do Power BI |
| Conversa | Perguntas de continuação ("e no Nordeste?") com as 3 últimas perguntas e SQLs da sessão | É como se usa de verdade; os resultados não entram no histórico, para economizar cota |

**Fora do escopo:** explicar o "porquê" lendo os documentos do projeto (busca em
documentos), login de visitante, limite global de uso, gravar as perguntas dos
visitantes.

## 3. Componentes

Pacote novo `agente/`, no padrão do `ml/`:

| Arquivo | Responsabilidade |
|---|---|
| `agente/config.py` | Variáveis de ambiente (provedores, modelos, chaves, conexão do usuário somente leitura) e a lista de tabelas permitidas |
| `agente/esquema.py` | Gera `agente/esquema_marts.md` a partir das descrições dos `.yml` do dbt e das colunas do banco: tabela, grão, colunas e significado. O arquivo é versionado, para mudança no prompt aparecer no diff |
| `agente/llm.py` | Cliente no formato da API da OpenAI; troca para o provedor de reserva no erro 429 (cota) e avisa quando os dois esgotaram |
| `agente/guarda_sql.py` | Valida o SQL com `sqlglot` antes de executar (seção 5) e força `LIMIT` |
| `agente/banco.py` | Conexão com `agente_leitura`, transação `READ ONLY`, `statement_timeout` de 5 s |
| `agente/numeros.py` | Checagem anti-invenção: extrai os números da resposta escrita e confere contra o resultado |
| `agente/grafico.py` | Regra que decide linha, barras ou nenhum gráfico pela forma do resultado |
| `agente/agente.py` | O fluxo da seção 4, sem Streamlit (testável) |
| `app.py` | Interface Streamlit: chat, resposta, tabela, SQL expansível, gráfico, perguntas de exemplo, rodapé com a data dos dados, limite por sessão |
| `scripts/criar_usuario_agente.sql` | Cria `agente_leitura` e as permissões; usado no Neon e no CI |

**Tabelas permitidas:** `fato_pedidos`, `fato_itens_pedido`, `dim_clientes`,
`dim_produtos`, `dim_vendedores`, `dim_tempo`, `dim_geolocalizacao` e
`previsao_atraso`, todas em `marts`. Ficam de fora as OBTs (o modelo misturaria
grãos), `seguranca_bi` (lista de acessos do Power BI) e `atualizacao_dados`
(lida pelo app para o rodapé, não pelo modelo).

## 4. Fluxo de uma pergunta

1. **Geração do SQL (chamada 1).** O prompt leva o esquema, as regras de negócio
   já usadas no Power BI e alguns exemplos de pergunta e SQL:
   - receita é `valor_total` de `fato_pedidos`; receita de itens é `valor_item`;
   - taxa de atraso e % no prazo contam só pedidos com `entregue_no_prazo` não
     nulo;
   - medidas de risco só com `conjunto` em `teste` ou `em_andamento`;
   - nunca somar métricas dos dois fatos na mesma consulta (grãos diferentes);
   - datas pela `dim_tempo` (`tempo_sk_compra`).

   Os exemplos são diferentes das perguntas da avaliação. O modelo devolve JSON
   com `sql` e um palpite de gráfico, ou `fora_do_escopo` com o motivo, quando a
   base não tem o dado (margem de lucro, nome de cliente).
2. **Guarda e execução.** O SQL passa pela guarda e roda no banco somente leitura.
   Se o banco devolver erro, uma nova tentativa manda o erro ao modelo. No máximo
   2 tentativas de SQL.
3. **Resposta (chamada 2).** O modelo recebe a pergunta, o SQL e até 50 linhas do
   resultado, e escreve de 1 a 3 frases em português.
4. **Checagem anti-invenção (sem modelo).** Cada número da resposta precisa
   aparecer no resultado, aceitando arredondamento e formato ("15,79 mi" contra
   15786203,57; "93,2%" contra 0,932). Se algum não bater, a frase é descartada:
   o app mostra a tabela e o aviso "resposta automática não confirmada".
5. **Gráfico (por regra).** Coluna de mês ou data com número: linha. Categoria com
   número e até 30 linhas: barras. Pedido explícito de gráfico vale quando o
   resultado permite. O palpite do modelo só desempata.

São 2 chamadas por pergunta, 3 com a nova tentativa.

## 5. Segurança

**No banco (a defesa que importa).** Usuário `agente_leitura`:
- `SELECT` concedido tabela por tabela, só nas permitidas;
- `default_transaction_read_only = on`, `statement_timeout = 5s` e limite de 3
  conexões, configurados no próprio usuário;
- sem acesso a outros schemas.

O `publicar_marts.py` apaga e recria as tabelas no Neon, o que apaga as
permissões. Ele passa a reaplicar os `GRANT` do agente no fim de cada publicação
(só se o usuário existir). Se a reaplicação falhar, o agente perde o acesso:
falha segura.

**Na guarda (`guarda_sql`)**, recusa:
- mais de um comando;
- qualquer coisa que não seja `SELECT` ou `WITH`, inclusive CTE que escreve
  (`WITH x AS (DELETE ...)`);
- tabela fora da lista permitida, inclusive com schema explícito (`raw.`,
  `meta.`, `pg_catalog.`);
- funções perigosas (`pg_sleep`, `set_config`, `dblink`, `pg_read_file` e
  parecidas).

E acrescenta `LIMIT 1000` quando não há limite.

**Na aplicação:**
- pergunta com no máximo 300 caracteres e 20 perguntas por sessão;
- cota esgotada nos dois provedores vira aviso, não erro;
- chaves e senha nos *secrets* do Streamlit e no `.env` local, nunca no Git;
- as perguntas dos visitantes não são gravadas.

**Limite registrado:** sem login nem limite global, um visitante insistente pode
esgotar a cota do dia abrindo várias sessões. Para um portfólio, é aceitável.

## 6. Testes e avaliação

**Testes automáticos (pytest, no CI, sem gastar cota):**
- `guarda_sql` com casos de ataque (os da seção 5) e com SQLs válidos que
  precisam passar;
- checagem de números: número do resultado passa, número inventado reprova,
  formatos brasileiros reconhecidos;
- regra do gráfico;
- fluxo do agente com modelo falso: SQL com erro seguido de correção, fora do
  escopo, cota esgotada com troca de provedor;
- permissões reais: o CI cria `agente_leitura` com o mesmo script do Neon e
  confirma que `SELECT` em `marts` funciona e que `DROP`, `INSERT`, leitura fora
  da lista e consulta acima do tempo falham.

**Avaliação de acerto (manual, gasta cota):** `agente/avaliacao/perguntas.yaml`
com cerca de 25 perguntas, cada uma com um SQL de referência:
- diretas ("receita de 2018");
- com junção ("taxa de atraso por região");
- de tempo ("variação da receita em mar/2018");
- de continuação ("e no Nordeste?");
- fora do escopo ("qual a margem de lucro?").

O script compara o **resultado** do agente com o do SQL de referência (não o
texto do SQL) e grava o relatório em `docs/agente.md`, com modelo, data, acertos
por tipo e os erros comentados.

**Metas:** pelo menos 80% de acerto nas perguntas dentro do escopo, 100% de
recusa nas de fora, nenhum SQL perigoso executado. Abaixo da meta, o resultado
fica registrado como está, como no modelo de atraso.

## 7. Publicação e documentação

- **Streamlit Community Cloud** a partir do repositório, com `app.py` na raiz. As
  dependências do app ficam num `requirements` próprio, para o deploy não instalar
  dbt nem scikit-learn.
- **Ações do dono** (contas e credenciais dele): criar o app no Streamlit Cloud
  com o GitHub, gerar as chaves gratuitas do Gemini (Google AI Studio) e do Groq,
  rodar o script do usuário no Neon com uma senha nova e colar tudo nos *secrets*.
  O passo a passo fica em `docs/agente.md`.
- No plano grátis o app dorme sem visitas e acorda em 30 a 60 segundos. Por isso o
  README leva um GIF curto de uma conversa, além do link.
- **Documentação:** `docs/agente.md` (arquitetura, defesas, avaliação, limites,
  como publicar), seção no README com o link e o GIF, ROADMAP com a Etapa 6
  concluída. O `requirements-extra.txt` deixa de prever o LangChain com OpenAI.

## 8. Critérios de pronto

1. Testes automáticos passando no CI, inclusive o de permissões.
2. Avaliação rodada e registrada em `docs/agente.md`.
3. App publicado no Streamlit Cloud, respondendo pelo link, com o GIF no README.
4. Varredura de segredo sem ocorrência (`npg_`, chaves de API).
5. README e ROADMAP atualizados; PR aberto com CI verde.
