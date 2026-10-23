-- Todo pedido com vendedor precisa ter distancia: o fallback de municipio e de
-- prefixo de 3 digitos existe para isso (issue #16). Um join quebrado deixaria
-- a coluna inteira nula, e o teste de plausibilidade passaria com zero casos.
-- Por isso este teste tambem falha quando nao ha nenhum pedido com vendedor.
with cobertura as (
    select
        count(*) filter (where vendedor_sk is not null)                            as com_vendedor,
        count(*) filter (where vendedor_sk is not null and distancia_km is null)   as sem_distancia
    from {{ ref('distancia_pedido') }}
)

select *
from cobertura
where com_vendedor = 0
   or sem_distancia > 0
