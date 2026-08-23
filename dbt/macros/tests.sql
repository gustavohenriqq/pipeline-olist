{#
  Testes genericos proprios (substituem os do dbt_utils).
  Ficam disponiveis como data_tests no schema.yml, igual aos nativos.
#}

{# Falha se a combinacao de colunas nao for unica (chave composta). #}
{% test combinacao_unica(model, combination_of_columns) %}
    select
        {{ combination_of_columns | join(', ') }},
        count(*) as n
    from {{ model }}
    group by {{ combination_of_columns | join(', ') }}
    having count(*) > 1
{% endtest %}


{# Falha se algum valor da coluna for menor que min_value. #}
{% test valor_minimo(model, column_name, min_value=0) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} < {{ min_value }}
{% endtest %}
