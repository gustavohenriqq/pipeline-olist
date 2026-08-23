-- Dimensao de geolocalizacao: um ponto por prefixo de CEP, com regiao.
with geo as (
    select * from {{ ref('stg_olist__geolocation') }}
)

select
    {{ gera_sk(['zip_code_prefix']) }} as geo_sk,
    zip_code_prefix,
    latitude,
    longitude,
    state                       as uf,
    {{ regiao_br('state') }}    as regiao
from geo
