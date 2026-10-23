## Tabelas disponíveis (schema marts)

### marts.fato_pedidos
Fato no grao de pedido, com metricas de valor, pagamento, nota e entrega.
Grão: um pedido.
- `pedido_sk` (text)
- `order_id` (text)
- `cliente_sk` (text): FK para dim_clientes.
- `geo_sk` (text): FK para dim_geolocalizacao (CEP do cliente). Alguns CEPs de cliente nao existem na base de geolocalizacao, por isso o teste e apenas aviso.
- `tempo_sk_compra` (integer): Liga em dim_tempo.tempo_sk (data da compra).
- `order_status` (text)
- `status_pedido` (text): order_status traduzido. Se a origem trouxer um status novo, a macro devolve o valor original em ingles em vez de esconder num 'Outro', e o teste abaixo acusa.
- `situacao_pedido` (text): 'Entregue', 'Em andamento' ou 'Não concluído'.
- `tipos_pagamento` (text)
- `qtd_itens` (bigint)
- `qtd_produtos_distintos` (bigint)
- `qtd_vendedores_distintos` (bigint)
- `valor_itens` (numeric): Soma dos preços dos itens, sem frete.
- `valor_frete` (numeric): Soma do frete dos itens.
- `valor_total` (numeric): Receita do pedido (itens + frete). É a receita padrão.
- `valor_pago` (numeric)
- `qtd_pagamentos` (bigint)
- `max_parcelas` (integer)
- `nota_avaliacao` (integer): Nota da avaliação do cliente, de 1 a 5; nula sem avaliação.
- `purchased_at` (timestamp without time zone)
- `approved_at` (timestamp without time zone)
- `delivered_carrier_at` (timestamp without time zone)
- `delivered_customer_at` (timestamp without time zone)
- `estimated_delivery_at` (timestamp without time zone)
- `tempo_entrega_dias` (integer): Dias da compra até a entrega ao cliente.
- `atraso_dias` (integer): Entrega menos data estimada, em dias: positivo é atraso, negativo é adiantado; nulo se não entregue.
- `dias_ate_transportadora` (integer): Dias entre a compra e a entrega do pacote a transportadora. E a parte do tempo sob responsabilidade do vendedor. Nulo quando coleta_fora_de_ordem e verdadeiro; fora isso, nunca negativo.
- `dias_em_transporte` (integer): Dias entre a coleta pela transportadora e a entrega ao cliente. E a parte do tempo sob responsabilidade da logistica. Nulo quando coleta_fora_de_ordem e verdadeiro; fora isso, nunca negativo.
- `coleta_fora_de_ordem` (boolean): Verdadeiro quando a data de coleta pela transportadora e anterior a compra (2 pedidos) ou posterior a entrega ao cliente (20 pedidos), erro de origem do Olist. Nesses 22 pedidos dias_ate_transportadora e dias_em_transporte ficam nulos; tempo_entrega_dias, atraso_dias e entregue_no_prazo continuam validos. O teste em aviso assert_coleta_fora_de_ordem_conhecida lista os casos.
- `foi_entregue` (boolean)
- `entregue_no_prazo` (boolean): true/false; nulo se o pedido não foi entregue. Taxa de atraso e % no prazo contam só os não nulos.

### marts.fato_itens_pedido
Fato no grao de item do pedido; conecta produto e vendedor.
Grão: um item de pedido (um pedido tem um ou mais itens, de vendedores e produtos diferentes).
- `item_sk` (text)
- `order_id` (text)
- `order_item_id` (integer)
- `produto_sk` (text): FK para dim_produtos.
- `vendedor_sk` (text): FK para dim_vendedores.
- `cliente_sk` (text)
- `tempo_sk_compra` (integer): Liga em dim_tempo.tempo_sk (data da compra do pedido).
- `valor_produto` (numeric)
- `valor_frete` (numeric)
- `valor_item` (numeric): Preço do item mais o frete do item. É a receita de itens.

### marts.dim_clientes
Dimensao de clientes no grao de pessoa (customer_unique_id).
Grão: um cliente (pessoa, customer_unique_id).
- `cliente_sk` (text): Chave substituta (surrogate key) do cliente.
- `customer_unique_id` (text)
- `zip_code_prefix` (integer)
- `cidade` (text)
- `uf` (text)
- `regiao` (text): Regiao do Brasil derivada da UF.

### marts.dim_produtos
Dimensao de produtos com categoria PT/EN e rotulos de leitura.
Grão: um produto.
- `produto_sk` (text)
- `product_id` (text)
- `categoria_pt` (text)
- `categoria_en` (text)
- `categoria_nome` (text): Nome da categoria formatado para leitura. Nunca nulo: produto sem categoria na origem vira 'Sem categoria'.
- `categoria_grupo` (text): Macro-categoria comercial. Agrupa as 73 categorias da origem em 14 grupos mais 'Sem categoria'. O teste de valores aceitos e a trava: categoria nova na origem cai em 'Diversos' e o teste avisa, em vez de o relatorio mostrar um grupo generico crescendo em silencio.
- `qtd_fotos` (integer)
- `peso_g` (numeric)
- `comprimento_cm` (numeric)
- `altura_cm` (numeric)
- `largura_cm` (numeric)
- `volume_cm3` (numeric)

### marts.dim_vendedores
Dimensao de vendedores.
Grão: um vendedor.
- `vendedor_sk` (text)
- `seller_id` (text)
- `zip_code_prefix` (integer)
- `cidade` (text)
- `uf` (text)
- `regiao` (text)
- `vendedor_rotulo` (text): Use para mostrar o vendedor (o seller_id é um hash).

### marts.dim_tempo
Dimensao de calendario diario.
Grão: um dia.
- `tempo_sk` (integer)
- `data` (date)
- `ano` (integer)
- `mes` (integer)
- `dia` (integer)
- `trimestre` (integer): 1 a 4.
- `dia_semana_num` (integer)
- `nome_mes` (text)
- `nome_dia_semana` (text)
- `fim_de_semana` (boolean)
- `ano_mes` (character varying): Texto 'AAAA-MM'.

### marts.dim_geolocalizacao
Dimensao de geolocalizacao por prefixo de CEP.
Grão: um prefixo de CEP.
- `geo_sk` (text)
- `zip_code_prefix` (integer)
- `latitude` (numeric)
- `longitude` (numeric)
- `uf` (text)
- `regiao` (text)

### marts.previsao_atraso
Probabilidade de atraso por pedido, com o limiar e a versao do modelo.
Grão: um pedido com previsão do modelo de atraso.
- `pedido_sk` (text)
- `prob_atraso` (numeric): Probabilidade de atraso prevista, de 0 a 1.
- `alerta` (boolean): true quando a probabilidade passa o limiar do modelo.
- `conjunto` (text): 'treino', 'validacao', 'teste' ou 'em_andamento'. Medidas de risco usam só 'teste' e 'em_andamento'.
- `limiar` (numeric)
- `modelo_versao` (text)
- `gerado_em` (timestamp with time zone)
