-- Um pedido pode ter mais de uma avaliacao. Ficamos com a mais recente,
-- para ter uma nota por pedido no fato.
with reviews as (
    select * from {{ ref('stg_olist__order_reviews') }}
),

ranked as (
    select
        order_id,
        review_score,
        created_at,
        row_number() over (
            partition by order_id
            order by created_at desc nulls last
        ) as rn
    from reviews
    where order_id is not null
)

select
    order_id,
    review_score,
    created_at as review_created_at
from ranked
where rn = 1
