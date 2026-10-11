"""Cartoes e graficos do painel, sem Streamlit."""
import pandas as pd

from agente.tema import PALETAS
from painel.cartoes import cartao, linha_de_cartoes, valor_br
from painel.graficos import barras_horizontais, barras_regiao, excesso_divergente, receita_com_ano_anterior


def test_cartao_escapa_texto_e_mostra_seta():
    html = cartao("<b>Receita</b>", "R$ 15,79 mi", "payments", "menta", -0.052)
    assert "&lt;b&gt;Receita&lt;/b&gt;" in html and "<b>Receita</b>" not in html
    assert "5,2%" in html and "vs. mês anterior" in html and "piora" in html


def test_cartao_subindo_e_melhora():
    assert "melhora" in cartao("Pedidos", "99.092", "receipt_long", "azul", 0.035)


def test_taxa_de_atraso_subindo_e_piora_em_pontos():
    html = cartao("Taxa de atraso", "6,8%", "schedule", "ambar", 2.8, taxa=True, piora_quando_sobe=True)
    assert "2,8 pp" in html and "piora" in html


def test_sem_mes_anterior_e_sem_dados():
    assert "sem mês anterior" in cartao("Receita", "R$ 1,00", "payments", "menta", None, sem_anterior=True)
    assert "vs. mês anterior" not in cartao("Itens", "112.279", "inventory_2", "violeta")
    assert valor_br(None, "moeda") == "sem dados"
    assert valor_br(float("nan"), "inteiro") == "sem dados"


def test_formatos_dos_cartoes():
    assert valor_br(15786203.57, "moeda_compacta") == "R$ 15,79 mi"
    assert valor_br(1573000.0, "moeda_compacta") == "R$ 1,57 mi"
    assert valor_br(99092, "inteiro") == "99.092"
    assert valor_br(159.3125, "moeda") == "R$ 159,31"
    assert valor_br(0.9322, "pct") == "93,2%"
    assert valor_br(4.0868, "nota") == "4,09"


def test_cor_desconhecida_nao_vira_classe_arbitraria():
    html = cartao("Receita", "R$ 1,00", "payments", 'menta" onclick="x')
    assert "onclick" not in html


def test_linha_de_cartoes():
    html = linha_de_cartoes([cartao("A", "1", "payments", "menta"), cartao("B", "2", "payments", "azul")])
    assert html.startswith('<div class="cartoes">') and html.count('class="cartao ') == 2


def test_excesso_divergente_pinta_acima_e_abaixo():
    df = pd.DataFrame({"uf": ["RJ", "SP"], "atraso_em_excesso": [659.0, -923.0]})
    spec = excesso_divergente(df, PALETAS["escuro"]).to_dict()
    assert spec["mark"]["type"] == "bar"
    cor = spec["encoding"]["color"]
    assert cor["condition"]["value"] == PALETAS["escuro"]["vermelho"]
    assert cor["value"] == PALETAS["escuro"]["destaque"]


def test_receita_com_ano_anterior_tem_area_e_linha():
    df = pd.DataFrame({"ano_mes": ["2018-01", "2018-02"], "receita": [1.1e6, 9.9e5],
                       "receita_ano_anterior": [1.2e5, 2.8e5]})
    spec = receita_com_ano_anterior(df, PALETAS["escuro"]).to_dict()
    marcas = [c["mark"]["type"] for c in spec["layer"]]
    assert marcas == ["area", "line"]


def test_barras_regiao_tem_a_taxa_nacional():
    df = pd.DataFrame({"regiao": ["Nordeste", "Sul"], "taxa_atraso": [0.12, 0.06], "taxa_nacional": [0.068, 0.068]})
    spec = barras_regiao(df, PALETAS["claro"]).to_dict()
    assert [c["mark"]["type"] for c in spec["layer"]] == ["bar", "rule"]


def test_barras_horizontais_genericas():
    df = pd.DataFrame({"categoria_grupo": ["Casa", "Moda"], "receita_itens": [3.2e6, 1.7e6]})
    spec = barras_horizontais(df, "categoria_grupo", "receita_itens", PALETAS["claro"]).to_dict()
    assert spec["mark"]["type"] == "bar" and spec["encoding"]["y"]["field"] == "categoria_grupo"
