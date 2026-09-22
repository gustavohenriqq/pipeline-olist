{#
  Rotulos para consumo humano (BI, agente de IA, relatorio).

  Por que aqui e nao num campo calculado do Looker Studio:
  o rotulo passa a existir uma vez so, versionado e testavel, e vale para todo
  consumidor do warehouse. Traduzir no Looker resolveria um relatorio e deixaria
  o Power BI e o agente de IA vendo os nomes crus de novo.

  As colunas de origem (order_status, categoria_pt) continuam nas marts. O
  rotulo e adicional, nunca substituicao: quem precisa do valor cru da fonte
  ainda o encontra.
#}


{#
  Status do pedido em portugues.
  Sao os 8 valores que existem na base do Olist. O ELSE devolve o valor original
  em vez de 'Outro': se a fonte inventar um status novo, ele aparece no relatorio
  como esta na origem, em vez de sumir dentro de um balde generico.
#}
{% macro status_pedido_pt(coluna) %}
    case {{ coluna }}
        when 'delivered'   then 'Entregue'
        when 'shipped'     then 'Enviado'
        when 'canceled'    then 'Cancelado'
        when 'unavailable' then 'Indisponivel'
        when 'invoiced'    then 'Faturado'
        when 'processing'  then 'Em processamento'
        when 'created'     then 'Criado'
        when 'approved'    then 'Aprovado'
        else {{ coluna }}
    end
{% endmacro %}


{#
  Nome da categoria formatado para leitura.
  A base tem 73 categorias em snake_case sem acento. O mapeamento e manual de
  proposito: traducao automatica trocaria underscore por espaco e devolveria
  "Cama Mesa Banho", que continua feio e sem acento.
#}
{% macro categoria_rotulo(coluna) %}
    case {{ coluna }}
        when 'agro_industria_e_comercio' then 'Agro, Industria e Comercio'
        when 'alimentos' then 'Alimentos'
        when 'alimentos_bebidas' then 'Alimentos e Bebidas'
        when 'artes' then 'Artes'
        when 'artes_e_artesanato' then 'Artes e Artesanato'
        when 'artigos_de_festas' then 'Artigos de Festas'
        when 'artigos_de_natal' then 'Artigos de Natal'
        when 'audio' then 'Audio'
        when 'automotivo' then 'Automotivo'
        when 'bebes' then 'Bebes'
        when 'bebidas' then 'Bebidas'
        when 'beleza_saude' then 'Beleza e Saude'
        when 'brinquedos' then 'Brinquedos'
        when 'cama_mesa_banho' then 'Cama, Mesa e Banho'
        when 'casa_conforto' then 'Casa e Conforto'
        when 'casa_conforto_2' then 'Casa e Conforto'
        when 'casa_construcao' then 'Casa e Construcao'
        when 'cds_dvds_musicais' then 'CDs e DVDs Musicais'
        when 'cine_foto' then 'Cine e Foto'
        when 'climatizacao' then 'Climatizacao'
        when 'consoles_games' then 'Consoles e Games'
        when 'construcao_ferramentas_construcao' then 'Construcao: Ferramentas'
        when 'construcao_ferramentas_ferramentas' then 'Construcao: Ferramentas'
        when 'construcao_ferramentas_iluminacao' then 'Construcao: Iluminacao'
        when 'construcao_ferramentas_jardim' then 'Construcao: Jardim'
        when 'construcao_ferramentas_seguranca' then 'Construcao: Seguranca'
        when 'cool_stuff' then 'Cool Stuff'
        when 'dvds_blu_ray' then 'DVDs e Blu-ray'
        when 'eletrodomesticos' then 'Eletrodomesticos'
        when 'eletrodomesticos_2' then 'Eletrodomesticos'
        when 'eletronicos' then 'Eletronicos'
        when 'eletroportateis' then 'Eletroportateis'
        when 'esporte_lazer' then 'Esporte e Lazer'
        when 'fashion_bolsas_e_acessorios' then 'Moda: Bolsas e Acessorios'
        when 'fashion_calcados' then 'Moda: Calcados'
        when 'fashion_esporte' then 'Moda: Esporte'
        when 'fashion_roupa_feminina' then 'Moda: Roupa Feminina'
        when 'fashion_roupa_infanto_juvenil' then 'Moda: Roupa Infantojuvenil'
        when 'fashion_roupa_masculina' then 'Moda: Roupa Masculina'
        when 'fashion_underwear_e_moda_praia' then 'Moda: Intima e Praia'
        when 'ferramentas_jardim' then 'Ferramentas e Jardim'
        when 'flores' then 'Flores'
        when 'fraldas_higiene' then 'Fraldas e Higiene'
        when 'industria_comercio_e_negocios' then 'Industria, Comercio e Negocios'
        when 'informatica_acessorios' then 'Informatica e Acessorios'
        when 'instrumentos_musicais' then 'Instrumentos Musicais'
        when 'la_cuisine' then 'La Cuisine'
        when 'livros_importados' then 'Livros Importados'
        when 'livros_interesse_geral' then 'Livros de Interesse Geral'
        when 'livros_tecnicos' then 'Livros Tecnicos'
        when 'malas_acessorios' then 'Malas e Acessorios'
        when 'market_place' then 'Marketplace'
        when 'moveis_colchao_e_estofado' then 'Moveis: Colchao e Estofado'
        when 'moveis_cozinha_area_de_servico_jantar_e_jardim' then 'Moveis: Cozinha e Jardim'
        when 'moveis_decoracao' then 'Moveis e Decoracao'
        when 'moveis_escritorio' then 'Moveis de Escritorio'
        when 'moveis_quarto' then 'Moveis: Quarto'
        when 'moveis_sala' then 'Moveis: Sala'
        when 'musica' then 'Musica'
        when 'papelaria' then 'Papelaria'
        when 'pc_gamer' then 'PC Gamer'
        when 'pcs' then 'Computadores'
        when 'perfumaria' then 'Perfumaria'
        when 'pet_shop' then 'Pet Shop'
        when 'portateis_casa_forno_e_cafe' then 'Portateis: Forno e Cafe'
        when 'portateis_cozinha_e_preparadores_de_alimentos' then 'Portateis: Cozinha'
        when 'relogios_presentes' then 'Relogios e Presentes'
        when 'seguros_e_servicos' then 'Seguros e Servicos'
        when 'sinalizacao_e_seguranca' then 'Sinalizacao e Seguranca'
        when 'tablets_impressao_imagem' then 'Tablets, Impressao e Imagem'
        when 'telefonia' then 'Telefonia'
        when 'telefonia_fixa' then 'Telefonia Fixa'
        when 'utilidades_domesticas' then 'Utilidades Domesticas'
        else coalesce(initcap(replace({{ coluna }}, '_', ' ')), 'Nao informada')
    end
{% endmacro %}


{#
  Macro-categoria: agrupa as 73 categorias em 14 grupos comerciais.

  Por que existe: com 73 opcoes, o filtro do BI vira uma lista impossivel de
  navegar, e o grafico de "top categorias" compara telefonia com telefonia_fixa
  como se fossem negocios diferentes. A base tambem traz duplicatas de origem
  (eletrodomesticos e eletrodomesticos_2, casa_conforto e casa_conforto_2) e
  cauda irrelevante (pc_gamer com 9 itens, seguros_e_servicos com 2).

  Regra do agrupamento: proximidade de uso comercial, nao de nome. Por isso
  telefonia fica com eletronicos, e nao sozinha, e as cinco variacoes de
  construcao viram um grupo so.

  Os 1.603 itens sem categoria na origem viram 'Nao informada' em vez de nulo,
  para aparecerem no relatorio em vez de sumirem silenciosamente.
#}
{% macro categoria_macro(coluna) %}
    case
        when {{ coluna }} is null then 'Nao informada'

        when {{ coluna }} in (
            'cama_mesa_banho', 'utilidades_domesticas', 'casa_conforto', 'casa_conforto_2',
            'moveis_decoracao', 'moveis_sala', 'moveis_quarto', 'moveis_colchao_e_estofado',
            'moveis_cozinha_area_de_servico_jantar_e_jardim',
            'portateis_casa_forno_e_cafe', 'portateis_cozinha_e_preparadores_de_alimentos',
            'la_cuisine', 'flores', 'artigos_de_natal', 'artigos_de_festas'
        ) then 'Casa e Decoracao'

        when {{ coluna }} in ('beleza_saude', 'perfumaria', 'fraldas_higiene')
            then 'Beleza e Saude'

        when {{ coluna }} in (
            'relogios_presentes', 'malas_acessorios', 'fashion_bolsas_e_acessorios',
            'fashion_calcados', 'fashion_esporte', 'fashion_roupa_feminina',
            'fashion_roupa_masculina', 'fashion_roupa_infanto_juvenil',
            'fashion_underwear_e_moda_praia'
        ) then 'Moda e Acessorios'

        when {{ coluna }} in ('esporte_lazer') then 'Esporte e Lazer'

        when {{ coluna }} in (
            'informatica_acessorios', 'pcs', 'pc_gamer', 'eletronicos', 'consoles_games',
            'audio', 'cine_foto', 'tablets_impressao_imagem', 'telefonia', 'telefonia_fixa'
        ) then 'Eletronicos e Informatica'

        when {{ coluna }} in (
            'eletrodomesticos', 'eletrodomesticos_2', 'eletroportateis', 'climatizacao'
        ) then 'Eletrodomesticos'

        when {{ coluna }} in (
            'ferramentas_jardim', 'casa_construcao', 'sinalizacao_e_seguranca',
            'construcao_ferramentas_construcao', 'construcao_ferramentas_ferramentas',
            'construcao_ferramentas_iluminacao', 'construcao_ferramentas_jardim',
            'construcao_ferramentas_seguranca'
        ) then 'Ferramentas e Construcao'

        when {{ coluna }} in ('brinquedos', 'bebes') then 'Bebes e Brinquedos'

        when {{ coluna }} in ('automotivo') then 'Automotivo'

        when {{ coluna }} in ('pet_shop') then 'Pet Shop'

        when {{ coluna }} in (
            'livros_interesse_geral', 'livros_tecnicos', 'livros_importados',
            'dvds_blu_ray', 'cds_dvds_musicais', 'musica', 'instrumentos_musicais',
            'artes', 'artes_e_artesanato'
        ) then 'Livros, Midia e Arte'

        when {{ coluna }} in ('alimentos', 'alimentos_bebidas', 'bebidas')
            then 'Alimentos e Bebidas'

        when {{ coluna }} in ('papelaria', 'moveis_escritorio')
            then 'Escritorio e Papelaria'

        when {{ coluna }} in (
            'agro_industria_e_comercio', 'industria_comercio_e_negocios', 'seguros_e_servicos'
        ) then 'Industria e Servicos'

        -- 'Diversos' e um grupo legitimo, nao um balde de sobra: 'cool_stuff' e a
        -- categoria guarda-chuva da propria Olist e sozinha vale R$ 719 mil, a
        -- oitava maior. Por isso entra aqui de forma explicita.
        when {{ coluna }} in ('cool_stuff', 'market_place') then 'Diversos'

        -- O ELSE e alarme, nao destino. Categoria nova na origem cai em
        -- 'Nao mapeada', que fica de fora da lista de valores aceitos e faz o
        -- teste avisar. Se o ELSE devolvesse 'Diversos', a categoria nova se
        -- esconderia dentro de um grupo valido e ninguem perceberia.
        else 'Nao mapeada'
    end
{% endmacro %}
