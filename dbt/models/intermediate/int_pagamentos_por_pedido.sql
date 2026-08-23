-- Um pedido pode ter varios pagamentos (ex: parte no voucher, parte no cartao).
-- Aqui reduzimos para uma linha por pedido, para usar no fato no grao de pedido.
with pagamentos as (
    select * from {{ ref('stg_olist__order_payments') }}
)

select
    order_id,
    count(*)                                   as qtd_pagamentos,
    sum(payment_value)                         as valor_pago,
    max(installments)                          as max_parcelas,
    string_agg(distinct payment_type, ', ' order by payment_type) as tipos_pagamento
from pagamentos
where order_id is not null
group by order_id
