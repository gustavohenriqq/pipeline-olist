-- Diagnostico do atraso: prazo mal calibrado ou entrega fora do padrao?
-- Uma linha por pedido entregue com data de entrega (subconjunto do grao de
-- fato_pedidos). Ver docs/analise-atraso.md, secao 7.
--
-- A pergunta: um pedido atrasou porque a promessa foi curta para a rota, ou
-- porque a entrega demorou mais do que a rota costuma demorar? As acoes sao
-- diferentes (recalibrar a estimativa contra mexer na malha logistica).
--
-- A regra, em tres passos:
--   1. Tempo tipico da rota: mediana do tempo real de entrega dos pedidos da
--      rota (UF do vendedor > UF do cliente). Rota com menos de
--      min_pedidos_rota pedidos, ou pedido com vendedores em mais de uma UF,
--      usa a mediana da UF do cliente.
--   2. Prazo padrao: tempo tipico vezes a razao prazo/tempo tipico mediana do
--      pais (2,21 na base completa). E a promessa que o pedido teria se a rota seguisse a mesma regua
--      das outras. A escala e proporcional, e nao em dias, porque a dispersao do
--      tempo de entrega cresce com o tempo tipico da rota (correlacao de 0,88
--      em dias e plana em razao, entre as 63 rotas com 100 pedidos ou mais).
--   3. Pedido atrasado que chegou dentro do prazo padrao e "prazo curto": com
--      a promessa padrao ele estaria no prazo. Atrasado que passou do prazo
--      padrao e "entrega lenta": atrasaria mesmo com a promessa padrao.
--
-- Diagnostico ex post: o tempo tipico usa a base inteira, inclusive pedidos
-- posteriores a cada compra. Nunca usar como feature do modelo de previsao,
-- porque vazaria o futuro.
--
-- Tabela cheia (nao incremental) de proposito: um pedido novo muda a mediana
-- da rota e, com ela, a classificacao de pedidos antigos.

{% set min_pedidos_rota = var('min_pedidos_rota', 30) %}

with pedidos as (
    select
        p.pedido_sk,
        p.order_id,
        c.uf                                                    as cliente_uf,
        c.regiao                                                as cliente_regiao,
        p.estimated_delivery_at::date - p.purchased_at::date    as prazo_prometido_dias,
        p.tempo_entrega_dias,
        p.entregue_no_prazo
    from {{ ref('fato_pedidos') }} p
    left join {{ ref('dim_clientes') }} c on c.cliente_sk = p.cliente_sk
    where p.foi_entregue
      and p.delivered_customer_at is not null
),

-- UF do vendedor no grao de pedido. 0,5% dos pedidos entregues tem
-- vendedores em mais de uma UF: ficam sem rota e usam a referencia da UF do
-- cliente, em vez de escolher um vendedor arbitrario.
vendedor_por_pedido as (
    select
        i.order_id,
        count(distinct v.uf)                                    as qtd_ufs_vendedor,
        min(v.uf)                                               as uf
    from {{ ref('fato_itens_pedido') }} i
    join {{ ref('dim_vendedores') }} v on v.vendedor_sk = i.vendedor_sk
    group by i.order_id
),

com_rota as (
    select
        p.*,
        case when vp.qtd_ufs_vendedor = 1 then vp.uf end        as vendedor_uf,
        case when vp.qtd_ufs_vendedor = 1
             then vp.uf || '>' || p.cliente_uf end              as rota
    from pedidos p
    left join vendedor_por_pedido vp on vp.order_id = p.order_id
),

tipico_rota as (
    select
        rota,
        count(*)                                                as pedidos_rota,
        percentile_cont(0.5) within group (order by tempo_entrega_dias) as tipico
    from com_rota
    where rota is not null
    group by rota
),

tipico_uf as (
    select
        cliente_uf,
        percentile_cont(0.5) within group (order by tempo_entrega_dias) as tipico
    from com_rota
    group by cliente_uf
),

com_tipico as (
    select
        r.*,
        case when tr.pedidos_rota >= {{ min_pedidos_rota }}
             then 'rota' else 'uf_cliente' end                  as referencia_tipico,
        (case when tr.pedidos_rota >= {{ min_pedidos_rota }}
              then tr.tipico else tu.tipico end)::numeric       as tempo_tipico_dias
    from com_rota r
    left join tipico_rota tr on tr.rota = r.rota
    left join tipico_uf  tu on tu.cliente_uf = r.cliente_uf
),

-- Regua do pais: quantas vezes o tempo tipico da rota o prazo prometido
-- costuma ser. Mediana sobre todos os pedidos da tabela, arredondada em duas
-- casas: sem o arredondamento, a mediana sai como 31/14 em ponto flutuante e
-- pedidos exatamente na fronteira (14 x 31/14 = 31 dias) trocavam de classe
-- conforme a precisao da conta (39 pedidos na primeira conferencia).
regua as (
    select
        round((percentile_cont(0.5) within group (
            order by prazo_prometido_dias / tempo_tipico_dias
        ))::numeric, 2)                                         as razao_prazo_padrao
    from com_tipico
    where tempo_tipico_dias > 0
)

select
    t.pedido_sk,
    t.order_id,
    t.cliente_uf,
    t.cliente_regiao,
    t.vendedor_uf,
    t.rota,
    t.prazo_prometido_dias,
    t.tempo_entrega_dias,
    -- Folga: prazo prometido menos tempo real. E o atraso_dias com sinal trocado.
    t.prazo_prometido_dias - t.tempo_entrega_dias               as folga_dias,
    t.referencia_tipico,
    t.tempo_tipico_dias,
    round(t.prazo_prometido_dias / nullif(t.tempo_tipico_dias, 0), 3) as prazo_sobre_tipico,
    round(t.tempo_entrega_dias  / nullif(t.tempo_tipico_dias, 0), 3) as tempo_sobre_tipico,
    g.razao_prazo_padrao,
    t.tempo_tipico_dias * g.razao_prazo_padrao                  as prazo_padrao_dias,
    t.entregue_no_prazo,
    case
        when t.entregue_no_prazo then null
        when t.tempo_entrega_dias <= t.tempo_tipico_dias * g.razao_prazo_padrao
            then 'prazo curto'
        else 'entrega lenta'
    end                                                         as causa_atraso
from com_tipico t
cross join regua g
