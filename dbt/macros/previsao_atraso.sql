-- Cria, vazia, a tabela onde o Python grava a previsao de atraso (ml/inferir.py).
--
-- Por que o DDL mora no dbt e nao no Python: a tabela e declarada como source
-- (ml_saida) e testada dentro do dbt build. Se ela so nascesse quando o
-- inferir.py roda, qualquer banco novo (inclusive o do CI) quebraria o build
-- com "relation does not exist". Com o hook on-run-start, a tabela sempre
-- existe; vazia, os testes passam. O Python so faz TRUNCATE + COPY.
--
-- "if not exists" mantem o hook idempotente: previsoes ja gravadas nao sao
-- apagadas por um dbt build. Mudar uma coluna aqui exige dropar a tabela.
{% macro cria_tabela_previsao() %}
    create schema if not exists marts;
    create table if not exists marts.previsao_atraso (
        pedido_sk      text,
        prob_atraso    numeric,
        alerta         boolean,
        conjunto       text,
        limiar         numeric,
        modelo_versao  text,
        gerado_em      timestamptz
    );
{% endmacro %}
