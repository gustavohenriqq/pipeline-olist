"""Filtros do painel: periodo, regiao, URL e o contexto que vai para o agente."""
from datetime import date

from painel.filtros import (MAXIMO, MINIMO, PADRAO, Filtros, contexto, da_selecao, da_url,
                            mes_anterior, mes_referencia, para_url)


def test_padrao_e_mes_de_referencia():
    assert PADRAO == Filtros(date(2017, 1, 1), date(2018, 8, 31), None)
    assert mes_referencia(PADRAO) == "2018-08"
    assert mes_anterior("2018-01") == "2017-12"
    assert mes_anterior("2018-08") == "2018-07"


def test_selecao_parcial_ou_invertida_mantem_o_atual():
    assert da_selecao((date(2018, 1, 1),), PADRAO) == PADRAO
    assert da_selecao(date(2018, 1, 1), PADRAO) == PADRAO
    assert da_selecao((), PADRAO) == PADRAO
    assert da_selecao((date(2018, 5, 1), date(2018, 1, 1)), PADRAO) == Filtros(date(2018, 1, 1), date(2018, 5, 1), None)


def test_selecao_mantem_a_regiao_atual():
    atual = Filtros(date(2017, 1, 1), date(2018, 8, 31), "Sul")
    assert da_selecao((date(2018, 1, 1), date(2018, 2, 1)), atual).regiao == "Sul"


def test_selecao_fora_dos_limites_e_cortada():
    f = da_selecao((date(2015, 1, 1), date(2019, 1, 1)), PADRAO)
    assert (f.inicio, f.fim) == (MINIMO, MAXIMO)


def test_filtros_iguais_tem_o_mesmo_hash():
    a = Filtros(date(2018, 1, 1), date(2018, 2, 1), "Sul")
    b = Filtros(date(2018, 1, 1), date(2018, 2, 1), "Sul")
    assert hash(a) == hash(b) and a == b


def test_url_ida_e_volta_e_lixo_cai_no_padrao():
    f = Filtros(date(2018, 1, 1), date(2018, 3, 31), "Nordeste")
    assert da_url(para_url(f)) == f
    assert da_url({"inicio": "abc", "regiao": "Marte"}) == PADRAO
    assert da_url({}) == PADRAO
    assert "regiao" not in para_url(PADRAO)


def test_contexto_para_o_agente():
    texto = contexto("Entrega e risco", Filtros(date(2018, 1, 1), date(2018, 8, 31), "Nordeste"))
    assert texto == "Contexto do painel: página Entrega e risco; período 01/01/2018 a 31/08/2018; região Nordeste."
    assert "região" not in contexto("Vendedores", PADRAO)


def test_janela_de_comparacao_como_o_power_bi():
    from painel.filtros import janela_comparacao
    d = date
    # mes inteiro contra o mes anterior inteiro
    assert janela_comparacao(PADRAO) == (d(2018, 8, 1), d(2018, 8, 31), d(2018, 7, 1), d(2018, 7, 31))
    # fim no meio do mes: 1 a 15 de agosto contra 1 a 15 de julho (nao julho inteiro)
    assert janela_comparacao(Filtros(d(2018, 1, 1), d(2018, 8, 15))) == (
        d(2018, 8, 1), d(2018, 8, 15), d(2018, 7, 1), d(2018, 7, 15))
    # inicio no meio do mes anterior: agosto inteiro contra julho inteiro
    assert janela_comparacao(Filtros(d(2018, 7, 20), d(2018, 8, 31))) == (
        d(2018, 8, 1), d(2018, 8, 31), d(2018, 7, 1), d(2018, 7, 31))
    # periodo dentro de um mes so
    assert janela_comparacao(Filtros(d(2018, 8, 10), d(2018, 8, 20))) == (
        d(2018, 8, 10), d(2018, 8, 20), d(2018, 7, 10), d(2018, 7, 20))
    # fim de mes curto vira fim do mes anterior
    assert janela_comparacao(Filtros(d(2018, 1, 1), d(2018, 3, 31)))[2:] == (d(2018, 2, 1), d(2018, 2, 28))
    assert janela_comparacao(Filtros(d(2018, 1, 1), d(2018, 2, 28)))[2:] == (d(2018, 1, 1), d(2018, 1, 31))


def test_mes_de_referencia_e_o_ultimo_com_venda_no_periodo():
    """Como o 'Mês de Referência' do Power BI: o ultimo mes com venda dentro do periodo."""
    from painel.filtros import janela_comparacao
    d = date
    # nov/2016 nao tem pedido: a referencia e out/2016 inteiro contra set/2016 inteiro
    f = Filtros(d(2016, 9, 1), d(2016, 11, 30))
    assert mes_referencia(f, d(2016, 10, 30)) == "2016-10"
    assert janela_comparacao(f, d(2016, 10, 30)) == (d(2016, 10, 1), d(2016, 10, 31), d(2016, 9, 1), d(2016, 9, 30))
    # ultima venda no mes do fim: a regra dos mesmos dias continua (1 a 15 de agosto contra julho)
    f = Filtros(d(2018, 1, 1), d(2018, 8, 15))
    assert janela_comparacao(f, d(2018, 8, 14)) == (d(2018, 8, 1), d(2018, 8, 15), d(2018, 7, 1), d(2018, 7, 15))
    # periodo dentro de um mes so: a janela nao passa do inicio do periodo
    f = Filtros(d(2018, 8, 10), d(2018, 9, 20))
    assert janela_comparacao(f, d(2018, 8, 29)) == (d(2018, 8, 10), d(2018, 8, 31), d(2018, 7, 10), d(2018, 7, 31))
    # sem venda no periodo: cai no mes do fim, como antes
    assert mes_referencia(PADRAO, None) == "2018-08"
