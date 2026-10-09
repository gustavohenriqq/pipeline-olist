# Conferência do modelo Power BI

Teste automático do modelo semântico: consulta por DAX o modelo aberto no Power BI
Desktop e compara com o mesmo número calculado em SQL nas marts.

| Arquivo | Papel |
|---|---|
| `casos.json` | a consulta DAX de cada caso |
| `esperado.sql` | o valor esperado de cada caso, calculado no Postgres |
| `conferir.ps1` | liga os dois e imprime `OK` ou `FALHOU` por caso |

## Como rodar

Com o Postgres local de pé e o `Olist.pbip` aberto e atualizado no Desktop:

```powershell
.\conferir.ps1                                   # contagens de linhas e medidas
.\conferir.ps1 -Grupos modelo                    # só as contagens de linhas
.\conferir.ps1 -Papel Diretoria                  # segurança de cada papel
.\conferir.ps1 -Papel "Gerente regional"
.\conferir.ps1 -Papel Vendedor
```

O script acha sozinho a porta do motor local do Desktop e usa a biblioteca de
cliente que vem com ele, então não precisa instalar nada. Sai com código 1 se
algum caso falhar.

## O que é conferido

- **Modelo:** linhas de cada tabela iguais às do banco.
- **Medidas:**
  - receita, pedidos, ticket médio, % no prazo e nota média;
  - atraso em excesso do RJ;
  - receita acumulada no ano até mar/2018 (no ano cheio o acumulado seria igual à
    receita e o caso não testaria nada);
  - variação mensal de mar/2018 e de set/2016 (o primeiro mês, que deve sair em
    branco, não em erro);
  - destaques dos cartões na janela padrão: receita e % no prazo de ago/2018
    contra jul/2018;
  - pedidos em alerta e receita em risco, só com teste e pedidos em andamento.
- **Segurança:** pedidos e itens visíveis em cada papel, e o OLS do Vendedor
  (as colunas de identificação do cliente precisam falhar no papel, e a mesma
  consulta precisa funcionar sem papel, para um erro de digitação não passar por
  bloqueio). Veja a
  seção seguinte.

## Segurança: o que é automático e o que é pelo "Exibir como"

O motor local do Desktop não aceita `EffectiveUserName` com um e-mail que não
seja conta do Windows (`O nome fornecido não é um nome de conta corretamente
formado`). Então o script entra só com o papel (`Roles`), e `USERPRINCIPALNAME()`
devolve o usuário do Windows, que não está em `seguranca_bi`. Isso testa
automaticamente o caso mais perigoso: **quem não está no seed vê zero** nos papéis
Gerente regional e Vendedor. Na Diretoria vê tudo, por desenho (quem controla o
acesso é a lista de membros do papel).

Os números de cada usuário do seed (e de um e-mail fora dele) são conferidos no Desktop, em Modelagem >
Exibir como > "Outro usuário" com o e-mail e o papel, olhando um visual com as
medidas Pedidos e Itens. O esperado sai do mesmo `esperado.sql` (linhas
`pedidos@<email>` e `itens@<email>`). Última conferência, em 09/10/2026:

| Usuário | Papel | Pedidos | Itens |
|---|---|---|---|
| diretoria@exemplo.com.br | Diretoria | 99.441 | 112.650 |
| gerente.nordeste@exemplo.com.br | Gerente regional | 9.399 | 10.413 |
| gerente.sudeste@exemplo.com.br | Gerente regional | 68.257 | 77.407 |
| vendedor.a@exemplo.com.br | Vendedor | 1.854 | 2.033 |
| vendedor.b@exemplo.com.br | Vendedor | 3.209 | 3.918 |
| fora@exemplo.com.br | Vendedor | vazio | vazio |

Todos iguais ao SQL. É o único passo manual da conferência: refazer quando mudar
um papel ou o seed.

## Por que um teste e não só olhar o visual

Um cartão com "R$ 15,84 mi" parece certo mesmo se a medida somar um pedido duas
vezes. A conferência compara até a casa dos centavos e roda de novo a cada
mudança no modelo. No RLS isso importa ainda mais: um filtro de segurança errado
não dá erro, só mostra dado de quem não devia.
