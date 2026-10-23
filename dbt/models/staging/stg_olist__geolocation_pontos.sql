-- Geolocalizacao no grao da origem: um ponto por linha, sem media por CEP.
--
-- Por que existe ao lado de stg_olist__geolocation: o fallback de distancia
-- (int_coordenadas_cep) precisa do municipio de cada ponto e de descartar
-- ponto a ponto o que cai fora do Brasil. A media por CEP ja perdeu as duas
-- coisas. stg_olist__geolocation continua igual, porque a dimensao e o mapa
-- do dashboard dependem dela.
with source as (
    select * from {{ source('raw', 'geolocation') }}
)

select
    cast(nullif(trim(geolocation_zip_code_prefix), '') as integer)  as zip_code_prefix,
    cast(nullif(trim(geolocation_lat), '') as float8)               as latitude,
    cast(nullif(trim(geolocation_lng), '') as float8)               as longitude,
    {{ chave_municipio('geolocation_city') }}                       as cidade_chave,
    upper(nullif(trim(geolocation_state), ''))                      as state
from source
where nullif(trim(geolocation_zip_code_prefix), '') is not null
