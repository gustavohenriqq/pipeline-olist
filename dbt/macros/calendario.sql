{#
  Gera uma serie de datas (uma por dia) entre start_date e end_date.
  Substitui o dbt_utils.date_spine para o projeto ficar sem dependencia externa.
  Retorna uma coluna date_day. Usa generate_series nativo do Postgres.
#}
{% macro calendario(start_date, end_date) -%}
    select cast(gs as date) as date_day
    from generate_series(
        cast({{ start_date }} as date),
        cast({{ end_date }} as date),
        interval '1 day'
    ) as gs
{%- endmacro %}
