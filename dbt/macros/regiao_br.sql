{#
  Mapeia a sigla do estado (UF) para a regiao do Brasil.
  Usado nas dimensoes de cliente, vendedor e geolocalizacao para permitir
  analises por regiao (Sudeste, Nordeste, etc.) no Power BI e no Looker.
#}
{% macro regiao_br(uf_column) %}
    case upper({{ uf_column }})
        when 'AC' then 'Norte'
        when 'AP' then 'Norte'
        when 'AM' then 'Norte'
        when 'PA' then 'Norte'
        when 'RO' then 'Norte'
        when 'RR' then 'Norte'
        when 'TO' then 'Norte'
        when 'AL' then 'Nordeste'
        when 'BA' then 'Nordeste'
        when 'CE' then 'Nordeste'
        when 'MA' then 'Nordeste'
        when 'PB' then 'Nordeste'
        when 'PE' then 'Nordeste'
        when 'PI' then 'Nordeste'
        when 'RN' then 'Nordeste'
        when 'SE' then 'Nordeste'
        when 'DF' then 'Centro-Oeste'
        when 'GO' then 'Centro-Oeste'
        when 'MT' then 'Centro-Oeste'
        when 'MS' then 'Centro-Oeste'
        when 'ES' then 'Sudeste'
        when 'MG' then 'Sudeste'
        when 'RJ' then 'Sudeste'
        when 'SP' then 'Sudeste'
        when 'PR' then 'Sul'
        when 'RS' then 'Sul'
        when 'SC' then 'Sul'
        else 'Desconhecida'
    end
{% endmacro %}
