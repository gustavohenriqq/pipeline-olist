-- Distancia em linha reta entre vendedor e cliente, uma linha por pedido.
--
-- Grao: o mesmo de fato_pedidos (todos os pedidos, inclusive sem item).
-- Vendedor: o do item de maior valor do pedido, a mesma regra de
-- ml_features_atraso. 98% dos pedidos tem um vendedor so.
--
-- Cobertura e metodo (detalhe em docs/analise-atraso.md, secao 1.1): 278
-- pedidos tem CEP de cliente fora da base de geolocalizacao e 253 itens tem
-- vendedor nessa situacao. Em vez de nulo, eles recebem o centroide do
-- municipio ou do prefixo de 3 digitos (int_coordenadas_cep), e a coluna
-- metodo_geo_* diz qual. Para analise que nao tolera aproximacao, filtre
-- distancia_por_cep.
--
-- Fica fora de fato_pedidos de proposito: o fato e incremental, com contrato
-- de schema (on_schema_change='fail'), e a distancia ainda e uma coluna
-- analitica, nao uma metrica do pedido.
with pedidos as (
    select pedido_sk, order_id from {{ ref('fato_pedidos') }}
),

orders as (
    select order_id, customer_id from {{ ref('stg_olist__orders') }}
),

customers as (
    select
        customer_id,
        zip_code_prefix,
        {{ chave_municipio('city') }} as cidade_chave,
        state                         as uf
    from {{ ref('stg_olist__customers') }}
),

sellers as (
    select
        seller_id,
        zip_code_prefix,
        {{ chave_municipio('city') }} as cidade_chave,
        state                         as uf
    from {{ ref('stg_olist__sellers') }}
),

item_principal as (
    select order_id, vendedor_sk, seller_id
    from (
        select
            i.order_id,
            i.vendedor_sk,
            v.seller_id,
            row_number() over (
                partition by i.order_id
                order by i.valor_item desc, i.order_item_id
            ) as rn
        from {{ ref('fato_itens_pedido') }} i
        join {{ ref('dim_vendedores') }} v on v.vendedor_sk = i.vendedor_sk
    ) t
    where rn = 1
),

coordenadas as (
    select * from {{ ref('int_coordenadas_cep') }}
),

base as (
    select
        p.pedido_sk,
        p.order_id,
        c.zip_code_prefix   as cliente_cep,
        c.uf                as cliente_uf,
        ip.vendedor_sk,
        s.zip_code_prefix   as vendedor_cep,
        s.uf                as vendedor_uf,
        gc.metodo_geo       as metodo_geo_cliente,
        gv.metodo_geo       as metodo_geo_vendedor,
        {{ distancia_haversine_km('gc.latitude', 'gc.longitude', 'gv.latitude', 'gv.longitude') }}
                            as distancia_km
    from pedidos p
    left join orders o          on o.order_id = p.order_id
    left join customers c       on c.customer_id = o.customer_id
    left join item_principal ip on ip.order_id = p.order_id
    left join sellers s         on s.seller_id = ip.seller_id
    left join coordenadas gc
        on gc.zip_code_prefix = c.zip_code_prefix and gc.cidade_chave = c.cidade_chave and gc.uf = c.uf
    left join coordenadas gv
        on gv.zip_code_prefix = s.zip_code_prefix and gv.cidade_chave = s.cidade_chave and gv.uf = s.uf
)

select
    pedido_sk,
    order_id,
    cliente_cep,
    cliente_uf,
    vendedor_sk,
    vendedor_cep,
    vendedor_uf,
    metodo_geo_cliente,
    metodo_geo_vendedor,
    round(distancia_km::numeric, 1) as distancia_km,
    -- Verdadeiro quando os dois pontos vem do proprio CEP, sem fallback.
    coalesce(metodo_geo_cliente = 'cep' and metodo_geo_vendedor = 'cep', false)
                                    as distancia_por_cep,
    -- Faixas para a tabela de controle do efeito do atraso (docs/analise-atraso.md).
    case
        when distancia_km is null  then 'Sem distância'
        when distancia_km < 100    then 'Até 100 km'
        when distancia_km < 500    then '100 a 500 km'
        when distancia_km < 1000   then '500 a 1.000 km'
        when distancia_km < 2000   then '1.000 a 2.000 km'
        else 'Acima de 2.000 km'
    end                             as faixa_distancia
from base
