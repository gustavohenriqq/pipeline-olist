with source as (
    select * from {{ source('raw', 'order_reviews') }}
),

renamed as (
    select
        nullif(trim(review_id), '')                      as review_id,
        nullif(trim(order_id), '')                       as order_id,
        cast(nullif(trim(review_score), '') as integer)  as review_score,
        nullif(trim(review_comment_title), '')           as comment_title,
        nullif(trim(review_comment_message), '')         as comment_message,
        cast(nullif(trim(review_creation_date), '') as timestamp)   as created_at,
        cast(nullif(trim(review_answer_timestamp), '') as timestamp) as answered_at
    from source
)

select * from renamed
