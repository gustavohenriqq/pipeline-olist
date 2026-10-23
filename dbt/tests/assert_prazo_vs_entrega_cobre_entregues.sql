-- prazo_vs_entrega precisa ter exatamente os pedidos entregues com data de
-- entrega do fato. Um join que perdesse pedidos mudaria a mediana das rotas e
-- o excesso por UF sem nenhum outro teste acusar.
with esperado as (
    select pedido_sk
    from {{ ref('fato_pedidos') }}
    where foi_entregue and delivered_customer_at is not null
)

select e.pedido_sk, 'falta na tabela' as problema
from esperado e
left join {{ ref('prazo_vs_entrega') }} v on v.pedido_sk = e.pedido_sk
where v.pedido_sk is null

union all

select v.pedido_sk, 'nao e entregue com data' as problema
from {{ ref('prazo_vs_entrega') }} v
left join esperado e on e.pedido_sk = v.pedido_sk
where e.pedido_sk is null
