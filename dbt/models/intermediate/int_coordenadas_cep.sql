-- Coordenada de cada endereco de cliente e de vendedor (CEP + municipio + UF),
-- com fallback para CEP que nao existe na base de geolocalizacao do Olist.
--
-- Ordem de preferencia (metodo_geo):
--   cep        media dos pontos do proprio prefixo de CEP (5 digitos)
--   municipio  centroide do municipio: media dos CEPs da mesma cidade e UF
--   prefixo_3  media dos CEPs com os mesmos 3 primeiros digitos
--   nulo       nenhum dos tres achou ponto
--
-- Por que municipio antes de prefixo_3: no teste de tirar um CEP conhecido e
-- estimar pelo resto (docs/analise-atraso.md, secao 1.1), o municipio erra
-- 4,7 km na mediana e 16 km no p90; o prefixo de 3 digitos erra 4,2 km na
-- mediana e 43 km no p90, porque no interior ele cobre varias cidades.
--
-- Ponto fora da caixa do Brasil e descartado ponto a ponto, antes da media
-- (ha CEP do PR com ponto na Espanha). Assim um ponto errado nao desloca o
-- CEP inteiro, e so perde a coordenada o CEP que nao tem nenhum ponto valido.
with pontos as (
    select *
    from {{ ref('stg_olist__geolocation_pontos') }}
    where latitude  between -33.8 and 5.3
      and longitude between -74.0 and -34.7
),

por_cep as (
    select
        zip_code_prefix,
        avg(latitude)                                       as latitude,
        avg(longitude)                                      as longitude,
        mode() within group (order by cidade_chave)         as cidade_chave,
        mode() within group (order by state)                as uf
    from pontos
    group by zip_code_prefix
),

-- Cada CEP pesa 1 no centroide, nao cada linha da origem: um CEP com
-- milhares de linhas nao puxa o municipio para si.
por_municipio as (
    select cidade_chave, uf, avg(latitude) as latitude, avg(longitude) as longitude
    from por_cep
    group by cidade_chave, uf
),

por_prefixo_3 as (
    select zip_code_prefix / 100 as prefixo_3, avg(latitude) as latitude, avg(longitude) as longitude
    from por_cep
    group by zip_code_prefix / 100
),

enderecos as (
    select zip_code_prefix, {{ chave_municipio('city') }} as cidade_chave, state as uf
    from {{ ref('stg_olist__customers') }}
    union
    select zip_code_prefix, {{ chave_municipio('city') }} as cidade_chave, state as uf
    from {{ ref('stg_olist__sellers') }}
)

select
    e.zip_code_prefix,
    e.cidade_chave,
    e.uf,
    coalesce(c.latitude,  m.latitude,  p.latitude)  as latitude,
    coalesce(c.longitude, m.longitude, p.longitude) as longitude,
    case
        when c.latitude is not null then 'cep'
        when m.latitude is not null then 'municipio'
        when p.latitude is not null then 'prefixo_3'
    end as metodo_geo
from enderecos e
left join por_cep c       on c.zip_code_prefix = e.zip_code_prefix
left join por_municipio m on m.cidade_chave = e.cidade_chave and m.uf = e.uf
left join por_prefixo_3 p on p.prefixo_3 = e.zip_code_prefix / 100
