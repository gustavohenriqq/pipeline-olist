-- A classificacao de prazo_vs_entrega precisa bater com a propria regra e com
-- o fato. Cada linha devolvida e uma violacao:
--   - causa preenchida em pedido no prazo, ou vazia em pedido atrasado;
--   - 'prazo curto' acima do prazo padrao, ou 'entrega lenta' dentro dele;
--   - folga diferente do atraso_dias do fato com o sinal trocado.
select
    v.pedido_sk,
    v.entregue_no_prazo,
    v.causa_atraso,
    v.tempo_entrega_dias,
    v.prazo_padrao_dias,
    v.folga_dias,
    f.atraso_dias
from {{ ref('prazo_vs_entrega') }} v
join {{ ref('fato_pedidos') }} f on f.pedido_sk = v.pedido_sk
where (v.entregue_no_prazo and v.causa_atraso is not null)
   or (not v.entregue_no_prazo and v.causa_atraso is null)
   or (v.causa_atraso = 'prazo curto'   and v.tempo_entrega_dias >  v.prazo_padrao_dias)
   or (v.causa_atraso = 'entrega lenta' and v.tempo_entrega_dias <= v.prazo_padrao_dias)
   or v.folga_dias <> -f.atraso_dias
