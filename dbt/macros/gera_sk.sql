{#
  Gera uma chave substituta (surrogate key) a partir de uma lista de colunas.
  Equivale ao dbt_utils.generate_surrogate_key, mas sem dependencia externa,
  para o projeto rodar em qualquer ambiente (inclusive sem acesso ao hub do dbt).

  Estrategia: concatena as colunas (tratando NULL como '') com um separador
  improvavel e aplica md5. Assim, chaves compostas nao colidem.
#}
{% macro gera_sk(field_list) -%}
    {%- set fields = [] -%}
    {%- for f in field_list -%}
        {%- set _ = fields.append("coalesce(cast(" ~ f ~ " as varchar), '')") -%}
    {%- endfor -%}
    md5({{ fields | join(" || '||' || ") }})
{%- endmacro %}
