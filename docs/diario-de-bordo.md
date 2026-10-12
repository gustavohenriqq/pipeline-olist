# Diário de bordo: erros, decisões de modelagem e tempo

Registro do que deu errado no caminho, de como cada erro foi percebido e do que
mudou depois. Um projeto de portfólio que só mostra o resultado final esconde a
parte que mais interessa a quem contrata: como a pessoa descobre que errou.

## Quanto tempo levou

Tempo **decorrido** entre o primeiro e o último commit de cada etapa, tirado do
histórico do Git. Não é hora trabalhada: não conta a leitura, o desenho e os testes
feitos antes do primeiro commit, e uma etapa que atravessa a noite aparece longa.
Serve para comparar o tamanho relativo das etapas, não para medir esforço.

| Etapa | Período | Commits | Tempo decorrido |
|---|---|---|---|
| 1. Fundação (ingestão, dbt, Neon) | 23/08/2026 | 8 | cerca de 2h30 no dia; o dashboard foi publicado em 08/10 |
| 2. Análise do atraso | 26/08/2026 | 4 | cerca de 8h30 (00:11 a 08:44) |
| Fatos incrementais (PR #2) | 30/09 a 02/10/2026 | 3 | 2 dias |
| 4. Previsão de atraso (PR #3) | 08/10/2026 | 10 | cerca de 1h (mais 45 min de desenho e plano antes) |
| 3. Confiabilidade no dbt (PR #4) | 08/10/2026 | 10 | cerca de 3h20 |
| 5. Power BI (PR #6) | 08/10 a 09/10/2026 | 14 | cerca de 15h, atravessando a noite |
| 6. Agente de IA (PR #7) | 10/10/2026 | 23 | cerca de 2h15, 7 deles correções |
| 7. Painel web com o agente (PR #8) | 10/10/2026 | 10 | cerca de 50 min |
| 8. HTML e CSS no Power BI (PR #9) | 12/10/2026 | 16 | cerca de 3h |

A numeração das etapas segue o plano; a ordem de entrega foi outra (a 4 saiu antes
da 3).

## Erros que chegaram a ser publicados

Os dois mais caros, porque ficaram visíveis antes de alguém perceber.

**"O Nordeste responde por 94% do atraso em excesso" (Etapa 2).** A conta estava
certa por região e a conclusão estava errada: agregado por região, o Rio de
Janeiro (+659 atrasos acima do esperado) ficava escondido dentro do Sudeste,
compensado por São Paulo (-923). Ficou **34 dias** publicado (26/08 a 29/09) e só
apareceu quando um mapa por estado pediu um grão mais fino. Correção: RJ (47%) e
Nordeste (38%) somam 86% do excesso. Lição: conclusão tirada num grão agregado
precisa ser conferida no grão de baixo antes de virar manchete. A correção ficou
visível no README, no ROADMAP e na análise, não foi apagada.

**"O dashboard já está publicado" (Etapa 1).** O README afirmava uma entrega que
ainda não existia. Corrigido em 2 minutos, mas a regra ficou: documentação
descreve o que existe, e o que falta aparece como pendente. Na Etapa 8 a revisão
final pegou o mesmo tipo de erro (o texto dava a entender que o Power BI já tinha
link público) antes do merge.

## Bugs que os testes pegaram

| Etapa | O bug | O que denunciou | Correção |
|---|---|---|---|
| 3 | O `dbt build` travou mais de 5 min num model de segundos: sem estatísticas na tabela recém-criada e com um CTE materializado, o planner estimou 418 bilhões de linhas | o próprio tempo do build | `analyze` depois de cada tabela e CTE não materializado: de 74 para 13 s, com md5 da tabela idêntico |
| 3 | O hook de metadados quebrava no parse completo (renderizado antes do grafo) e quebraria com uma aspa na mensagem de erro | build com `--no-partial-parse` | guarda `if not execute` e macro que escapa aspas, com teste |
| 4 | 493 pedidos com distância de 20 mil km: no Postgres, `least(1, null)` devolve 1, não nulo | teste dbt de distância plausível (até 4.500 km) | `case` no lugar de `least` |
| 4 | O mês da compra "decorava" 2017: o modelo perdia até para a baseline | validação temporal e PSI de 4,92 na coluna | feature removida; a primeira execução continua versionada |
| 5 | Em DAX, `BLANK() = FALSE()` é verdadeiro: a medida de atrasos contava os 2.965 pedidos sem entrega (9.500 em vez de 6.535) | primeira execução da conferência DAX contra SQL | `==` no lugar de `=` |
| 6 | A checagem de números do agente descartava frases certas: o rótulo do vendedor tem dígitos ("Ibitinga/SP · 4a3ca9") | avaliação com 25 perguntas de resposta conhecida | dígitos dentro de célula de texto contam como conferidos |
| 6 | Respostas com "2016.0" e "2017.0000000000002" e valores sem formato brasileiro | uso real do app | ano inteiro e números no formato pt-BR |
| 6 | Comparação em 2 casas empatava taxas diferentes (0,0812 e 0,0789) | revisão final | taxas em 4 casas, totais no centavo |
| 7 | Estado da tela guardado em variável de módulo: visitantes simultâneos trocavam a coluna do agente um do outro | revisão final | estado por sessão, nunca no módulo |
| 7 | O CI do painel rodava contra tabelas mínimas, sem as marts, e falhava | revisão final | PR que mexe no painel constrói as marts inteiras e confere os números num passo próprio |
| 7 | Os destaques comparavam um mês parcial com o mês anterior inteiro | revisão final | mesmos dias deslocados um mês, como o `DATEADD` do Power BI |
| 8 | Com filtro de região, o eixo do gráfico de receita mostrava "0,0 Mi" em todas as linhas | revisão final independente | unidade escolhida pelo tamanho (mil ou Mi), com caso na conferência |
| 8 | O script da cópia pública podia apagar o repositório com um `-Destino` errado | revisão final, provado num teste em pasta temporária | recusa destino acima da origem e só apaga pasta que ele mesmo gerou |
| 8 | A lista de atraso em excesso por UF cortava no fim e escondia SP (-926), metade da história | conferência visual dos prints | lista com rolagem |

## Armadilhas de ferramenta

Não são bugs do projeto, mas custaram rodadas de tentativa e erro. A lista
completa está em cada documento; aqui ficam as que mudariam o planejamento de
quem fosse refazer.

- **Looker Studio:** renomear um rótulo no dbt ("Casa e Decoracao" para "Casa e
  Decoração") apagou as cores do gráfico, que são chaveadas pelo texto. Mudar
  rótulo é mudança que quebra o BI, mesmo sem mudar número. Uma métrica chamada
  "Clientes" contava pedidos: o rótulo estava errado, não só feio. Detalhes em
  [dashboards/README.md](../dashboards/README.md).
- **Power BI Desktop:** salvar sobrescreve o TMDL editado por fora; a exportação
  para PDF só desenha o HTML da página aberta, na escala do zoom, e guarda cache
  por visual; texto em degradê sai como bloco no PDF. Detalhes em
  [dashboards/powerbi/README.md](../dashboards/powerbi/README.md).
- **Windows:** a política de controle de aplicativos bloqueia o `dbt.exe` e, em
  alguns momentos, a DLL do pandas. O dbt roda por `python -m`, e os testes que
  dependem do pandas rodam no CI.

## Decisões de modelagem

As que mais influenciaram o resto do projeto, com o motivo:

- **Raw tudo em texto.** Nenhum casting na ingestão; o casting fica no staging,
  versionado e testável. O bruto nunca é perdido.
- **Dois fatos, dois grãos.** `fato_pedidos` (pedido) e `fato_itens_pedido` (item).
  Produto e vendedor só existem no grão de item, porque um pedido tem vários.
  Somar métricas dos dois grãos na mesma visão infla a receita.
- **Cliente é a pessoa** (`customer_unique_id`), não o `customer_id`, que muda a
  cada pedido. Com o id errado, "clientes que voltaram" seria quase zero por
  construção.
- **OBT não substitui o star schema.** As tabelas largas existem porque o Looker
  só junta fontes por blend; Power BI e agente leem o star.
- **Fatos incrementais por comparação, não por data.** Os CSVs não têm uma data
  de atualização confiável, então cada fato compara o resultado atual com o
  destino (`EXCEPT`) e reescreve só o que mudou. Ver
  [incrementalidade.md](incrementalidade.md).
- **Problema conhecido vira teste em aviso.** 278 CEPs sem geolocalização e 22
  pedidos com data impossível são avisos documentados, não erros escondidos.
- **Neon recebe só as marts.** A tabela crua de geolocalização tem 1 milhão de
  linhas e o free tier tem 0,5 GB; BI nunca lê a camada crua.

O que foi cortado (PySpark, Airflow, previsão de demanda, coorte), e por quê,
está no [ROADMAP](../ROADMAP.md#decisões-descartadas-e-por-quê).
