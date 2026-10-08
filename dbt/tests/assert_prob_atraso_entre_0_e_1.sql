-- Probabilidade fora de [0, 1] indica bug na inferencia (ml/inferir.py).
select pedido_sk, prob_atraso
from {{ source('ml_saida', 'previsao_atraso') }}
where prob_atraso < 0 or prob_atraso > 1
