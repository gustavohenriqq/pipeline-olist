with source as (
    select * from {{ source('raw', 'geolocation') }}
),

renamed as (
    select
        cast(nullif(trim(geolocation_zip_code_prefix), '') as integer)  as zip_code_prefix,
        cast(nullif(trim(geolocation_lat), '') as numeric)  as latitude,
        cast(nullif(trim(geolocation_lng), '') as numeric)  as longitude,
        initcap(nullif(trim(geolocation_city), ''))         as city,
        upper(nullif(trim(geolocation_state), ''))          as state
    from source
),

-- A raw tem varias linhas por CEP. Guardamos um ponto medio por prefixo,
-- que e o suficiente para agregacao regional no BI.
dedup as (
    select
        zip_code_prefix,
        avg(latitude)  as latitude,
        avg(longitude) as longitude,
        max(state)     as state
    from renamed
    where zip_code_prefix is not null
    group by zip_code_prefix
)

select * from dedup
