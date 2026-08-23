{#
  Por padrao o dbt cria schemas no formato <target>_<custom> (ex: analytics_marts).
  Aqui simplificamos para usar o nome do schema como esta (staging, intermediate, marts).
  Fica mais limpo para o BI e o agente apontarem.

  Observacao de producao: nomes de schema fixos sao otimos para um projeto local,
  mas em um data warehouse compartilhado por varios devs isso causaria colisao.
  Nesse caso, o padrao <target>_<custom> (comportamento default do dbt) e mais seguro.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
