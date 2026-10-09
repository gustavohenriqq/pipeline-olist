-- Os papeis do Power BI usam todas as linhas do e-mail, sem olhar o perfil; o
-- esperado.sql da conferencia filtra pelo perfil. Linha incoerente faria os dois
-- divergirem em silencio: Gerente so com regiao, Vendedor so com seller_id,
-- Diretoria sem nenhum dos dois, e cada e-mail com um perfil so.
select email, perfil, regiao, seller_id
from {{ ref('seguranca_bi') }}
where (perfil = 'Diretoria' and (regiao is not null or seller_id is not null))
   or (perfil = 'Gerente regional' and (regiao is null or seller_id is not null))
   or (perfil = 'Vendedor' and (seller_id is null or regiao is not null))

union all

select email, perfil, regiao, seller_id
from {{ ref('seguranca_bi') }}
where email in (
    select email from {{ ref('seguranca_bi') }}
    group by email
    having count(distinct perfil) > 1
)
