-- Mesma trava de assert_distancia_km_plausivel, agora na mart: a maior
-- distancia entre dois pontos do Brasil fica perto de 4.400 km. Acima disso e
-- bug, como ponto nulo virando 20 mil km. Tambem pega um fallback que devolva
-- coordenada fora do pais.
select pedido_sk, distancia_km, metodo_geo_cliente, metodo_geo_vendedor
from {{ ref('distancia_pedido') }}
where distancia_km > 4500
