# Dashboards

## Looker Studio (publico, Fase 1)

O Looker Studio le direto de um Postgres. Duas opcoes:

1. **Postgres local:** so funciona enquanto sua maquina esta ligada e exposta. Nao serve para um portfolio online.
2. **Neon (recomendado):** Postgres serverless e gratuito na nuvem. Suba as tabelas `marts` para o Neon e conecte o Looker nele. Assim o dashboard fica no ar 24/7.

Passos:
1. Criar um projeto no [Neon](https://neon.tech) e pegar a string de conexao.
2. Rodar o dbt apontando o profile para o Neon (basta trocar as variaveis do `.env`).
3. No Looker Studio: Criar fonte de dados -> PostgreSQL -> preencher host, banco, usuario e senha do Neon -> escolher as tabelas `marts.fato_pedidos`, `marts.dim_clientes`, etc.
4. Montar as paginas (visao geral, regioes, vendedores, entregas, satisfacao).
5. Publicar e colar o link aqui e no README.

> Dica: o mesmo padrao ja foi usado no projeto Copa 2026. Reaproveite a conexao.

Link do dashboard: _sera adicionado ao final da Fase 1._

## Power BI (Fase 4)

- Conectar via Import ao Postgres/Azure SQL.
- Como o star schema ja vem pronto do dbt, no Power BI so ligue os relacionamentos (fato -> dimensoes pelas chaves `_sk`).
- Medidas DAX, RLS por regiao/vendedor e OLS para metricas sensiveis.

Os arquivos `.pbix` e os prints ficam nesta pasta e em `docs/prints/`.
