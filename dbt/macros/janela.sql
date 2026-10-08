{#
  Reprocessamento dos fatos por janela de datas da compra (Etapa 3).
  Ver docs/confiabilidade.md e docs/incrementalidade.md.

  dbt build --select fato_pedidos fato_itens_pedido \
    --vars '{janela_inicio: 2018-03-01, janela_fim: 2018-04-01}'

  Com a janela, num build incremental, o pre_hook apaga do fato as linhas do
  periodo e o model insere as atuais, na mesma transacao: correcoes e exclusoes
  da origem dentro da janela entram; o que esta fora fica intocado. Sem as vars,
  os fatos seguem a comparacao completa com EXCEPT.
#}

{% macro janela_reprocessamento() %}
    {%- set inicio = var('janela_inicio', none) -%}
    {%- set fim = var('janela_fim', none) -%}
    {%- if inicio is none and fim is none -%}
        {{ return(none) }}
    {%- endif -%}
    {%- set uso = "Use as duas vars juntas, no formato AAAA-MM-DD, com fim exclusivo: "
        ~ "--vars '{janela_inicio: 2018-03-01, janela_fim: 2018-04-01}'" -%}
    {%- if inicio is none or fim is none -%}
        {{ exceptions.raise_compiler_error(
            "Janela incompleta: falta " ~ ('janela_fim' if fim is none else 'janela_inicio') ~ ". " ~ uso) }}
    {%- endif -%}
    {%- set inicio = inicio | string -%}
    {%- set fim = fim | string -%}
    {%- for valor in (inicio, fim) -%}
        {%- if not modules.re.match('^[0-9]{4}-[0-9]{2}-[0-9]{2}$', valor) -%}
            {{ exceptions.raise_compiler_error("Data invalida na janela: " ~ valor ~ ". " ~ uso) }}
        {%- endif -%}
        {#- strptime rejeita datas impossiveis, como 2018-02-30 -#}
        {%- do modules.datetime.datetime.strptime(valor, '%Y-%m-%d') -%}
    {%- endfor -%}
    {%- if inicio >= fim -%}
        {{ exceptions.raise_compiler_error(
            "Janela vazia ou invertida: " ~ inicio ~ " a " ~ fim ~ ". " ~ uso) }}
    {%- endif -%}
    {{ return({'inicio': inicio, 'fim': fim}) }}
{% endmacro %}


{#- Condicao SQL da janela. tipo 'data' para timestamp; 'sk' para o inteiro AAAAMMDD. -#}
{% macro filtro_janela(coluna, tipo='data') %}
    {%- set janela = janela_reprocessamento() -%}
    {%- if tipo == 'sk' -%}
        {{ coluna }} >= {{ janela.inicio | replace('-', '') }} and {{ coluna }} < {{ janela.fim | replace('-', '') }}
    {%- else -%}
        {{ coluna }} >= '{{ janela.inicio }}' and {{ coluna }} < '{{ janela.fim }}'
    {%- endif -%}
{% endmacro %}


{#- pre_hook dos fatos: so apaga com janela definida e build incremental. -#}
{% macro apaga_janela(coluna, tipo='data') %}
    {%- if janela_reprocessamento() is not none and is_incremental() -%}
        delete from {{ this }} where {{ filtro_janela(coluna, tipo) }}
    {%- endif -%}
{% endmacro %}


{#- Corpo do incremental: filtro da janela, ou o EXCEPT da comparacao completa. -#}
{% macro delta_incremental(coluna, tipo='data') %}
    {%- set janela = janela_reprocessamento() -%}
    {%- if execute and janela is not none and not is_incremental() -%}
        {%- do log("Janela " ~ janela.inicio ~ " a " ~ janela.fim ~ " ignorada em " ~ this
            ~ ": build nao incremental (tabela nova ou --full-refresh) reconstroi tudo.", info=True) -%}
    {%- endif -%}
    {%- if is_incremental() and janela is not none %}
where {{ filtro_janela(coluna, tipo) }}
    {%- elif is_incremental() %}
-- O CSV nao tem updated_at: comparamos o resultado inteiro, incluindo NULLs,
-- para detectar novos registros e correcoes antigas sem uma janela arbitraria.
-- delete+insert substitui por chave somente as linhas retornadas pelo EXCEPT.
except
select * from {{ this }}
    {%- endif %}
{% endmacro %}
