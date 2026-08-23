-- Teste singular: nenhum pedido pode ter valor total negativo.
-- Se este teste retornar linhas, o dbt marca falha.
select
    order_id,
    valor_total
from {{ ref('fato_pedidos') }}
where valor_total < 0
