-- Dimensao de vendedores, com regiao para analise geografica.
with sellers as (
    select * from {{ ref('stg_olist__sellers') }}
),

-- A cidade do vendedor vem suja na origem ("Sp / Sp", "Rio De Janeiro, Rio De
-- Janeiro, Brasil", CEP, e-mail). Para o rotulo fica so a parte antes de '/' ou
-- ',', e some quando sobra numero, e-mail ou so a sigla.
cidade_rotulo as (
    select
        seller_id,
        nullif(trim(split_part(split_part(city, '/', 1), ',', 1)), '') as cidade
    from sellers
)

select
    {{ gera_sk(['s.seller_id']) }} as vendedor_sk,
    s.seller_id,
    s.zip_code_prefix,
    s.city                        as cidade,
    s.state                       as uf,
    {{ regiao_br('s.state') }}    as regiao,
    -- O Olist anonimiza o vendedor (hash de 32 caracteres). O rotulo e para
    -- leitura humana: cidade/UF e os 6 primeiros caracteres, unicos na base.
    case
        when c.cidade is null or c.cidade ~ '^[0-9]+$' or c.cidade like '%@%'
            or length(c.cidade) <= 2
            then s.state
        else c.cidade || '/' || s.state
    end || ' · ' || left(s.seller_id, 6) as vendedor_rotulo
from sellers s
join cidade_rotulo c on c.seller_id = s.seller_id
