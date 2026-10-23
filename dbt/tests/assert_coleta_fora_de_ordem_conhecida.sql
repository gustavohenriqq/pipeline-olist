{{ config(severity='warn') }}

-- Teste singular em aviso: lista os pedidos com coleta_fora_de_ordem (22 na
-- base do Olist, erro de origem). Fica em aviso para o caso continuar visivel
-- em todo build, e um numero diferente de 22 pede investigacao. Decisao de
-- tratamento em docs/analise-atraso.md, secao 5.
select
    order_id,
    purchased_at,
    delivered_carrier_at,
    delivered_customer_at
from {{ ref('fato_pedidos') }}
where coleta_fora_de_ordem
