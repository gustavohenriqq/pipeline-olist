-- A maior distancia entre dois pontos do Brasil fica perto de 4.400 km.
-- Valor acima disso e bug no calculo, como CEP sem coordenada virando a
-- distancia maxima da Terra (cerca de 20 mil km) em vez de nulo.
select pedido_sk, distancia_km
from {{ ref('ml_features_atraso') }}
where distancia_km > 4500
