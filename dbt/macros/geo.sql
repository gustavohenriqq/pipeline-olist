{#
  Chave de municipio para casar cidade de cliente/vendedor com a base de
  geolocalizacao. As duas fontes escrevem o mesmo municipio de jeitos
  diferentes: a geolocalizacao tem "são paulo" (24.917 linhas) e "sao paulo"
  (135.800), "santa bárbara d'oeste" e "santa barbara d'oeste". A chave tira
  acento, apostrofo, hifen e espaco repetido. Usada so para juntar, nunca
  para exibir.
#}
{% macro chave_municipio(coluna) %}
    nullif(
        regexp_replace(
            translate(
                lower(trim({{ coluna }})),
                'áàâãäéèêëíìîïóòôõöúùûüç''-',
                'aaaaaeeeeiiiiooooouuuuc  '
            ),
            '\s+', ' ', 'g'
        ),
        ''
    )
{% endmacro %}


{#
  Distancia em linha reta (haversine, raio da Terra 6371 km) entre dois pontos.
  Nulo quando falta qualquer coordenada. O case de fora e obrigatorio: no
  Postgres, least(1, null) devolve 1, e um ponto nulo viraria 20 mil km (meia
  volta na Terra) em vez de nulo. O least() de dentro so protege o asin de
  arredondamento acima de 1.
#}
{% macro distancia_haversine_km(lat1, lng1, lat2, lng2) %}
    case
        when {{ lat1 }} is null or {{ lng1 }} is null
          or {{ lat2 }} is null or {{ lng2 }} is null then null
        else 2 * 6371 * asin(least(1.0, sqrt(
            power(sin(radians({{ lat2 }} - {{ lat1 }}) / 2), 2)
            + cos(radians({{ lat1 }})) * cos(radians({{ lat2 }}))
              * power(sin(radians({{ lng2 }} - {{ lng1 }}) / 2), 2)
        )))
    end
{% endmacro %}
