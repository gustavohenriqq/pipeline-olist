-- Dimensao de tempo (calendario diario) cobrindo o periodo do dataset.
-- Uma dim_tempo propria evita depender de funcoes de data no BI e deixa
-- os filtros (ano, mes, trimestre, fim de semana) prontos e consistentes.
with dias as (
    {{ calendario("'2016-01-01'", "'2019-01-01'") }}
),

base as (
    select cast(date_day as date) as data from dias
)

select
    cast(to_char(data, 'YYYYMMDD') as integer) as tempo_sk,
    data,
    extract(year from data)::int   as ano,
    extract(month from data)::int  as mes,
    extract(day from data)::int    as dia,
    extract(quarter from data)::int as trimestre,
    -- 0 = domingo ... 6 = sabado (padrao do Postgres)
    extract(dow from data)::int    as dia_semana_num,
    case extract(month from data)::int
        when 1 then 'Janeiro'   when 2 then 'Fevereiro' when 3 then 'Marco'
        when 4 then 'Abril'     when 5 then 'Maio'      when 6 then 'Junho'
        when 7 then 'Julho'     when 8 then 'Agosto'    when 9 then 'Setembro'
        when 10 then 'Outubro'  when 11 then 'Novembro' when 12 then 'Dezembro'
    end as nome_mes,
    case extract(dow from data)::int
        when 0 then 'Domingo'  when 1 then 'Segunda' when 2 then 'Terca'
        when 3 then 'Quarta'   when 4 then 'Quinta'  when 5 then 'Sexta'
        when 6 then 'Sabado'
    end as nome_dia_semana,
    (extract(dow from data)::int in (0, 6)) as fim_de_semana,
    cast(to_char(data, 'YYYY-MM') as varchar) as ano_mes
from base
