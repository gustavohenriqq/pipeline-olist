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
.\conferir.ps1 -Papel "Gerente regional" -Usuario gerente.nordeste@exemplo.com.br
.\conferir.ps1 -Papel Vendedor -Usuario vendedor.a@exemplo.com.br
```

O script acha sozinho a porta do motor local do Desktop e usa a biblioteca de
cliente que vem com ele, então não precisa instalar nada. Sai com código 1 se
algum caso falhar.

## O que é conferido

- **Modelo:** linhas de cada tabela iguais às do banco.
- **Medidas:**
  - receita, pedidos, ticket médio, % no prazo e nota média;
  - atraso em excesso do RJ;
  - receita acumulada de 2018;
  - variação mensal de mar/2018 e de set/2016 (o primeiro mês, que deve sair em
    branco, não em erro);
  - pedidos em alerta e receita em risco, só com teste e pedidos em andamento.
- **Segurança:** para cada usuário do seed, pedidos e itens visíveis no papel
  dele, comparados com a mesma regra escrita em SQL. Um e-mail fora do seed deve
  ver zero. No papel Vendedor, as colunas de identificação do cliente precisam
  falhar por permissão (OLS).

## Por que um teste e não só olhar o visual

Um cartão com "R$ 15,84 mi" parece certo mesmo se a medida somar um pedido duas
vezes. A conferência compara até a casa dos centavos e roda de novo a cada
mudança no modelo. No RLS isso importa ainda mais: um filtro de segurança errado
não dá erro, só mostra dado de quem não devia.
