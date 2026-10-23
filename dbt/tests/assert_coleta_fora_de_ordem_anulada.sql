-- Teste singular: a flag coleta_fora_de_ordem e as duas metricas que dependem
-- da data de coleta andam juntas.
--   1. Pedido marcado nao pode ter dias_ate_transportadora nem
--      dias_em_transporte (seriam o -171 e o 178 que puxam medias).
--   2. Pedido nao marcado, com coleta e entrega registradas, precisa ter as duas
--      metricas: a regra nao pode anular pedido bom.
-- Se este teste retornar linhas, o dbt marca falha.
select
    order_id,
    coleta_fora_de_ordem,
    dias_ate_transportadora,
    dias_em_transporte
from {{ ref('fato_pedidos') }}
where (
        coleta_fora_de_ordem
        and (dias_ate_transportadora is not null or dias_em_transporte is not null)
    )
    or (
        not coleta_fora_de_ordem
        and delivered_carrier_at is not null
        and delivered_customer_at is not null
        and (dias_ate_transportadora is null or dias_em_transporte is null)
    )
