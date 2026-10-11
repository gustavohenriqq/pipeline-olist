"""Apresentacao das respostas: texto, nomes de coluna, formatos e grafico."""
import pandas as pd

from agente.apresentacao import escapar_markdown, formato_coluna, grafico, rotulo_coluna


def test_cifrao_nao_vira_formula():
    texto = escapar_markdown("De R$ 57.183,21 em 2016 até R$ 8.643.697,60 em 2018.")
    assert "$" not in texto.replace("\\$", "")
    assert texto.count("\\$") == 2


def test_rotulo_de_coluna_legivel():
    assert rotulo_coluna("receita_total") == "Receita total"
    assert rotulo_coluna("ano_mes") == "Mês"
    assert rotulo_coluna("uf") == "UF"
    assert rotulo_coluna("taxa_atraso") == "Taxa atraso"


def test_ano_e_mes_sem_separador_de_milhar():
    assert formato_coluna("ano", pd.Series([2016, 2017])) == "plain"
    assert formato_coluna("trimestre", pd.Series([1, 2])) == "plain"


def test_valores_com_formato_local():
    assert formato_coluna("receita_total", pd.Series([57183.21, 7142672.43])) == "localized"


def test_texto_sem_formato_numerico():
    assert formato_coluna("uf", pd.Series(["SP", "RJ"])) is None


def _spec(df, tipo):
    return grafico(df, tipo).to_dict()


def test_grafico_de_barras_com_eixo_compacto_e_comecando_no_zero():
    df = pd.DataFrame({"ano": [2016, 2017, 2018], "receita_total": [57183.21, 7142672.43, 8643697.60]})
    spec = _spec(df, "barras")
    assert spec["mark"]["type"] == "bar"
    assert spec["encoding"]["x"]["field"] == "ano"
    assert spec["encoding"]["x"]["type"] == "nominal"
    assert spec["encoding"]["x"]["axis"]["labelAngle"] == 0
    assert spec["encoding"]["y"]["axis"]["format"] == "~s"
    assert spec["encoding"]["y"]["scale"]["zero"] is True
    assert spec["encoding"]["y"]["title"] == "Receita total"


def test_grafico_de_linha_com_mes():
    df = pd.DataFrame({"ano_mes": ["2018-01", "2018-02"], "pedidos": [7269, 6728]})
    spec = _spec(df, "linha")
    assert spec["mark"]["type"] == "line"
    assert spec["encoding"]["x"]["title"] == "Mês"
