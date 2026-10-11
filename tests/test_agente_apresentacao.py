"""Apresentacao das respostas: texto, nomes de coluna, formatos e grafico."""
from decimal import Decimal

import pandas as pd

from agente.apresentacao import escapar_markdown, formatadores, grafico, preparar, rotulo_coluna


def test_cifrao_nao_vira_formula():
    texto = escapar_markdown("De R$ 57.183,21 em 2016 até R$ 8.643.697,60 em 2018.")
    assert "$" not in texto.replace("\\$", "")
    assert texto.count("\\$") == 2


def test_rotulo_de_coluna_legivel():
    assert rotulo_coluna("receita_total") == "Receita total"
    assert rotulo_coluna("ano_mes") == "Mês"
    assert rotulo_coluna("uf") == "UF"
    assert rotulo_coluna("taxa_atraso") == "Taxa atraso"


def test_ano_que_vem_como_decimal_vira_inteiro():
    df = preparar(pd.DataFrame({"ano": [Decimal("2016"), 2017.0000000000002, Decimal("2018")],
                                "receita_total": [Decimal("57183.21"), Decimal("7142672.43"),
                                                  Decimal("8643697.60")]}))
    assert list(df["ano"]) == [2016, 2017, 2018]
    assert pd.api.types.is_integer_dtype(df["ano"])
    assert pd.api.types.is_float_dtype(df["receita_total"])


def _formatado(nome, valores, valor):
    df = preparar(pd.DataFrame({nome: valores}))
    return formatadores(df)[nome](valor)


def test_ano_sem_separador_de_milhar():
    assert _formatado("ano", [2016, 2017], 2017) == "2017"


def test_valor_com_duas_casas_no_formato_brasileiro():
    assert _formatado("receita_total", [57183.21, 8643697.6], 8643697.6) == "8.643.697,60"


def test_contagem_com_milhar_e_sem_casas():
    assert _formatado("pedidos", [99441, 7269], 99441) == "99.441"


def test_taxa_com_quatro_casas():
    assert _formatado("ticket_medio_variacao", [0.0812, 0.1203], 0.0812) == "0,0812"


def test_texto_sem_formatador():
    assert "uf" not in formatadores(pd.DataFrame({"uf": ["SP", "RJ"], "pedidos": [1, 2]}))


def _spec(df, tipo):
    return grafico(df, tipo).to_dict()


def test_grafico_de_barras_comecando_no_zero():
    df = pd.DataFrame({"ano": [2016, 2017, 2018], "receita_total": [57183.21, 7142672.43, 8643697.60]})
    spec = _spec(df, "barras")
    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["x"]["field"] == "ano"
    assert spec["encoding"]["x"]["type"] == "nominal"
    assert spec["encoding"]["x"]["axis"]["labelAngle"] == 0
    assert spec["encoding"]["y"]["scale"]["zero"] is True
    assert spec["encoding"]["y"]["title"] == "Receita total"


def test_eixo_do_valor_em_mil_e_mi():
    df = pd.DataFrame({"ano": [2017, 2018], "receita_total": [7142672.43, 8643697.60]})
    expressao = _spec(df, "barras")["encoding"]["y"]["axis"]["labelExpr"]
    assert "' mi'" in expressao and "' mil'" in expressao


def test_ano_inteiro_no_eixo_sem_ponto_zero():
    df = preparar(pd.DataFrame({"ano": [Decimal("2016"), Decimal("2017")], "receita": [1.0, 2.0]}))
    linhas = next(iter(_spec(df, "barras")["datasets"].values()))
    assert [linha["ano"] for linha in linhas] == ["2016", "2017"]


def test_grafico_de_linha_com_mes():
    df = pd.DataFrame({"ano_mes": ["2018-01", "2018-02"], "pedidos": [7269, 6728]})
    spec = _spec(df, "linha")
    assert spec["mark"]["type"] == "line"
    assert spec["encoding"]["x"]["title"] == "Mês"


def test_tabela_html_formata_e_escapa():
    from agente.apresentacao import tabela_html
    df = preparar(pd.DataFrame({"uf": ["<b>SP</b>", "RJ"], "pedidos": [99441, 7269]}))
    html = tabela_html(df)
    assert "&lt;b&gt;SP&lt;/b&gt;" in html and "<b>SP</b>" not in html
    assert "99.441" in html
    assert '<td class="num">' in html
    assert "<th>UF</th>" in html and '<th class="num">Pedidos</th>' in html


def test_grafico_usa_cores_da_paleta():
    from agente.tema import PALETAS
    escuro = PALETAS["escuro"]
    df = pd.DataFrame({"ano": [2017, 2018], "receita_total": [1.0, 2.0]})
    spec = grafico(df, "barras", escuro).to_dict()
    assert spec["mark"]["color"] == escuro["destaque"]
    assert spec["config"]["axis"]["labelColor"] == escuro["texto_suave"]


def test_coluna_de_tempo_alinhada_como_rotulo():
    from agente.apresentacao import tabela_html
    html = tabela_html(preparar(pd.DataFrame({"ano": [2017, 2018], "pedidos": [45101, 54011]})))
    assert "<th>Ano</th>" in html and "<td>2017</td>" in html
    assert '<td class="num">45.101</td>' in html


def test_taxa_entre_zero_e_um_vira_percentual():
    assert _formatado("taxa_atraso", [0.2141, 0.1374], 0.2141) == "21,41%"
    assert _formatado("percentual_no_prazo", [0.9188], 0.9188) == "91,88%"


def test_taxa_fora_de_zero_a_um_fica_numero():
    assert _formatado("taxa_atraso", [12.5, 8.1], 12.5) == "12,50"


def test_eixo_de_taxa_em_percentual():
    df = pd.DataFrame({"uf": ["AL", "MA"], "taxa_atraso": [0.2141, 0.1746]})
    assert _spec(df, "barras")["encoding"]["y"]["axis"]["format"] == ".0%"


def test_variacao_em_percentual_mesmo_acima_de_um_e_negativa():
    assert _formatado("variacao_mensal", [1.087, -0.052], 1.087) == "108,70%"
    assert _formatado("variacao_mensal", [1.087, -0.052], -0.052) == "-5,20%"


def test_rotulos_do_placar():
    assert rotulo_coluna("pct_no_prazo") == "% no prazo"
    assert rotulo_coluna("ticket_medio") == "Ticket médio"
    assert rotulo_coluna("variacao_mensal") == "Var. mensal"


def test_tabela_html_com_classe_por_linha():
    from agente.apresentacao import tabela_html
    df = preparar(pd.DataFrame({"uf": ["RJ", "SP"], "prob_atraso": [0.52, 0.31]}))
    html = tabela_html(df, classe_linha=lambda linha: "risco-alto" if linha["prob_atraso"] >= 0.4 else "")
    assert '<tr class="risco-alto">' in html and html.count("risco-alto") == 1


def test_data_na_tabela_no_formato_brasileiro():
    from datetime import date
    from agente.apresentacao import tabela_html
    html = tabela_html(pd.DataFrame({"compra": [date(2018, 7, 29)], "uf": ["RJ"]}))
    assert "<td>29/07/2018</td>" in html
