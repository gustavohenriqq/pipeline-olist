{#
  Metadados de execucao do dbt (Etapa 3). Ver docs/confiabilidade.md.

  on-run-start: cria_tabelas_metadados() garante o schema meta e as tabelas.
  on-run-end:   grava_metadados(results) registra a invocacao e cada no, e,
                so no "dbt build", reescreve marts.atualizacao_dados, a linha
                que o rodape do dashboard le no Neon.

  Sem pacote do hub (dbt_artifacts): o projeto nao usa dependencias externas.
#}

{% macro cria_tabelas_metadados() %}
    create schema if not exists meta;
    create table if not exists meta.execucoes_dbt (
        invocation_id  text primary key,
        comando        text,
        iniciado_em    timestamptz,
        terminado_em   timestamptz,
        alvo           text,
        versao_dbt     text,
        nos            integer,
        sucesso        integer,
        aviso          integer,
        erro           integer,
        pulados        integer
    );
    create table if not exists meta.resultados_dbt (
        invocation_id  text,
        unique_id      text,
        tipo           text,
        nome           text,
        status         text,
        falhas         integer,
        segundos       numeric,
        mensagem       text
    );
    create schema if not exists marts;
    create table if not exists marts.atualizacao_dados (
        processado_em  timestamptz,
        carga_raw_em   timestamptz,
        testes_ok      integer,
        testes_aviso   integer,
        testes_erro    integer,
        resumo         text
    );
{% endmacro %}


{# Literal SQL seguro: aspas simples dobradas, truncado, null para vazio. #}
{% macro texto_sql(valor, limite=500) -%}
    {%- if valor is none or (valor | string | trim) == '' -%}
        null
    {%- else -%}
        '{{ (valor | string)[:limite] | replace("'", "''") }}'
    {%- endif -%}
{%- endmacro %}


{# Usada pelo scripts/validate_incremental.py: dbt run-operation testa_texto_sql #}
{% macro testa_texto_sql() %}
    {% set consulta %}
        select
            {{ texto_sql("it's") }} = 'it''s',
            length({{ texto_sql('x' * 600) }}) = 500,
            {{ texto_sql(none) }} is null
    {% endset %}
    {% set linha = run_query(consulta).rows[0] %}
    {% if not (linha[0] and linha[1] and linha[2]) %}
        {{ exceptions.raise_compiler_error("texto_sql nao escapou, truncou ou tratou nulo como esperado") }}
    {% endif %}
    {{ log("texto_sql ok", info=True) }}
{% endmacro %}


{% macro grava_metadados(results) %}
    {#- No parse o hook e renderizado sem grafo nem resultados: nada a gravar. -#}
    {%- if not execute -%}
        {{ return('') }}
    {%- endif -%}
    {%- set ns = namespace(sucesso=0, aviso=0, pulados=0, t_ok=0, t_aviso=0, t_erro=0) -%}
    {%- for r in results -%}
        {%- set st = r.status | string -%}
        {%- if st in ('success', 'pass') -%}{%- set ns.sucesso = ns.sucesso + 1 -%}
        {%- elif st == 'warn' -%}{%- set ns.aviso = ns.aviso + 1 -%}
        {%- elif st in ('skipped', 'no-op', 'reused') -%}{%- set ns.pulados = ns.pulados + 1 -%}
        {%- endif -%}
        {%- if r.node.resource_type == 'test' -%}
            {%- if st == 'pass' -%}{%- set ns.t_ok = ns.t_ok + 1 -%}
            {%- elif st == 'warn' -%}{%- set ns.t_aviso = ns.t_aviso + 1 -%}
            {%- elif st in ('fail', 'error') -%}{%- set ns.t_erro = ns.t_erro + 1 -%}
            {%- endif -%}
        {%- endif -%}
    {%- endfor -%}
    {#- erro e o resto: garante sucesso + aviso + erro + pulados = nos -#}
    {%- set erro = results | length - ns.sucesso - ns.aviso - ns.pulados -%}

    insert into meta.execucoes_dbt values (
        '{{ invocation_id }}', {{ texto_sql(flags.WHICH) }},
        '{{ run_started_at }}'::timestamptz, now(),
        {{ texto_sql(target.name) }}, {{ texto_sql(dbt_version) }},
        {{ results | length }}, {{ ns.sucesso }}, {{ ns.aviso }}, {{ erro }}, {{ ns.pulados }}
    );

    {% if results | length > 0 %}
    insert into meta.resultados_dbt values
    {%- for r in results %}
        ('{{ invocation_id }}', {{ texto_sql(r.node.unique_id) }}, {{ texto_sql(r.node.resource_type) }},
         {{ texto_sql(r.node.name) }}, {{ texto_sql(r.status | string) }},
         {{ r.failures if r.failures is number else 'null' }},
         {{ r.execution_time if r.execution_time is number else 'null' }},
         {{ texto_sql(r.message) }}){{ "," if not loop.last }}
    {%- endfor %};
    {% endif %}

    {#- O rodape descreve o projeto inteiro: so um build completo o reescreve.
        Build com --select/--exclude/--selector (como o "make reprocessar")
        contaria so parte dos testes e diria "processado agora" sobre o resto. -#}
    {%- set args = invocation_args_dict -%}
    {%- set build_completo = flags.WHICH == 'build'
        and not args.get('select') and not args.get('exclude') and not args.get('selector') -%}
    {% if build_completo %}
    truncate marts.atualizacao_dados;
    insert into marts.atualizacao_dados
    select
        now(),
        (
            select max(carga) from (
                {%- for fonte in graph.sources.values() if fonte.source_name == 'raw' %}
                select max(_carregado_em) as carga from {{ fonte.schema }}.{{ fonte.identifier }}
                {{- " union all" if not loop.last }}
                {%- endfor %}
            ) cargas
        ),
        {{ ns.t_ok }}, {{ ns.t_aviso }}, {{ ns.t_erro }},
        'Dados processados em '
            || to_char(now() at time zone 'America/Sao_Paulo', 'DD/MM/YYYY HH24:MI')
            || ' (Brasília) · {{ ns.t_ok }} testes ok, {{ ns.t_aviso }} avisos'
            {#- erro conta qualquer no (model ou teste); um model quebrado nao
                pode aparecer como "tudo ok" so porque os testes dele foram pulados. -#}
            {%- if erro > 0 %} || ', {{ erro }} erros'{% endif %}
            {%- if ns.pulados > 0 %} || ', {{ ns.pulados }} pulados'{% endif %};
    {% endif %}
{% endmacro %}
