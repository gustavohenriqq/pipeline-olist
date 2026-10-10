"""Esquema das marts para o prompt: so tabelas permitidas, com grao e descricoes."""
from agente.config import TABELAS_PERMITIDAS
from agente.esquema import ler_descricoes, montar_esquema

YML = """
version: 2
models:
  - name: dim_clientes
    description: Dimensao de clientes no grao de pessoa.
    columns:
      - name: regiao
        description: Regiao do Brasil derivada da UF.
  - name: obt_pedidos
    description: Tabela larga para o Looker.
sources:
  - name: ml_saida
    tables:
      - name: previsao_atraso
        description: Probabilidade de atraso por pedido.
        columns:
          - name: prob_atraso
            description: Probabilidade entre 0 e 1.
"""


def _colunas():
    colunas = {t: [("id", "integer")] for t in TABELAS_PERMITIDAS}
    colunas["dim_clientes"] = [("cliente_sk", "text"), ("uf", "text"), ("regiao", "text")]
    colunas["previsao_atraso"] = [("pedido_sk", "text"), ("prob_atraso", "double precision")]
    colunas["obt_pedidos"] = [("pedido_sk", "text")]
    colunas["seguranca_bi"] = [("email", "text")]
    return colunas


def test_le_descricoes_de_models_e_sources(tmp_path):
    caminho = tmp_path / "x.yml"
    caminho.write_text(YML, encoding="utf-8")
    d = ler_descricoes(caminho)
    assert d["dim_clientes"]["colunas"]["regiao"] == "Regiao do Brasil derivada da UF."
    assert d["previsao_atraso"]["descricao"] == "Probabilidade de atraso por pedido."


def test_so_tabelas_permitidas(tmp_path):
    caminho = tmp_path / "x.yml"
    caminho.write_text(YML, encoding="utf-8")
    texto = montar_esquema(_colunas(), ler_descricoes(caminho))
    for tabela in TABELAS_PERMITIDAS:
        assert f"marts.{tabela}" in texto
    assert "obt_pedidos" not in texto
    assert "seguranca_bi" not in texto


def test_cada_tabela_tem_grao():
    texto = montar_esquema(_colunas(), {})
    blocos = texto.split("### ")[1:]
    assert len(blocos) == len(TABELAS_PERMITIDAS)
    assert all("Grão:" in bloco for bloco in blocos)


def test_colunas_com_tipo_e_descricao(tmp_path):
    caminho = tmp_path / "x.yml"
    caminho.write_text(YML, encoding="utf-8")
    texto = montar_esquema(_colunas(), ler_descricoes(caminho))
    assert "`regiao` (text): Regiao do Brasil derivada da UF." in texto
    assert "`prob_atraso` (double precision)" in texto


def test_esquema_cabe_no_prompt():
    assert len(montar_esquema(_colunas(), {})) < 12000
