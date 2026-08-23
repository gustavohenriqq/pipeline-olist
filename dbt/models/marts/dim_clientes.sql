-- Dimensao de clientes no grao de PESSOA (customer_unique_id).
-- Na base do Olist, customer_id muda a cada pedido; customer_unique_id
-- identifica a mesma pessoa. Para uma dimensao de cliente, o certo e a pessoa.
with customers as (
    select * from {{ ref('stg_olist__customers') }}
),

-- Uma pessoa pode ter varios customer_id (um por pedido). Escolhemos uma
-- linha de referencia de forma deterministica para pegar cidade/estado/CEP.
ranked as (
    select
        customer_unique_id,
        customer_id,
        zip_code_prefix,
        city,
        state,
        row_number() over (
            partition by customer_unique_id
            order by customer_id
        ) as rn
    from customers
)

select
    {{ gera_sk(['customer_unique_id']) }} as cliente_sk,
    customer_unique_id,
    zip_code_prefix,
    city                        as cidade,
    state                       as uf,
    {{ regiao_br('state') }}    as regiao
from ranked
where rn = 1
