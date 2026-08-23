-- Dimensao de vendedores, com regiao para analise geografica.
with sellers as (
    select * from {{ ref('stg_olist__sellers') }}
)

select
    {{ gera_sk(['seller_id']) }} as vendedor_sk,
    seller_id,
    zip_code_prefix,
    city                        as cidade,
    state                       as uf,
    {{ regiao_br('state') }}    as regiao
from sellers
