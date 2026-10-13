"""Estrutura do relatorio Power BI (PBIR) e do tema, sem abrir o Desktop.

A conferencia dos numeros fica em dashboards/powerbi/conferencia (DAX contra SQL);
aqui so o que esta nos arquivos: tema, paginas e quais visuais usam quais medidas.
"""
import json
from pathlib import Path

RELATORIO = Path(__file__).resolve().parents[1] / "dashboards" / "powerbi" / "Olist.Report"
TEMA = RELATORIO / "StaticResources" / "RegisteredResources" / "tema-olist.json"
VISUAL_HTML = "STANDALONEhtmlContent443BE3AD55E043BF878BED274D3A6855"


def _ler(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _tema() -> dict:
    return _ler(TEMA)


def _paginas() -> dict[str, Path]:
    """Nome de exibicao da pagina -> pasta da pagina."""
    pastas = (RELATORIO / "definition" / "pages").glob("*/page.json")
    return {_ler(p)["displayName"]: p.parent for p in pastas}


def _visuais(pagina: str) -> list[dict]:
    return [_ler(v) for v in (_paginas()[pagina] / "visuals").glob("*/visual.json")]


def test_tres_paginas_do_relatorio():
    assert set(_paginas()) == {"Executivo", "Entrega e risco", "Vendedores"}


def test_tema_segue_o_painel_web():
    tema = _tema()
    assert tema["background"] == "#070B1A"
    assert tema["foreground"] == "#E8ECFF"
    assert tema["dataColors"][:3] == ["#22D3EE", "#8B5CF6", "#EC4899"]
    pagina = tema["visualStyles"]["page"]["*"]["background"][0]["color"]["solid"]["color"]
    assert pagina == "#070B1A"
    fundo_visual = tema["visualStyles"]["*"]["*"]["background"][0]["color"]["solid"]["color"]
    assert fundo_visual == "#121A3A"


def test_visual_html_registrado_no_relatorio():
    pacotes = [p["name"] for p in _ler(RELATORIO / "definition" / "report.json")["resourcePackages"]]
    assert VISUAL_HTML in pacotes
    assert (RELATORIO / "CustomVisuals" / VISUAL_HTML / "package.json").exists()


def _medidas_html(pagina: str) -> set[str]:
    medidas = set()
    for v in _visuais(pagina):
        if v["visual"]["visualType"] != VISUAL_HTML:
            continue
        for p in v["visual"]["query"]["queryState"]["content"]["projections"]:
            medidas.add(p["field"]["Measure"]["Property"])
    return medidas


def _tem_visual(pagina: str, tipo: str) -> bool:
    return any(v["visual"]["visualType"] == tipo for v in _visuais(pagina))


def _dentro_da_pagina(pagina: str) -> bool:
    return all(v["position"]["x"] + v["position"]["width"] <= 1920
               and v["position"]["y"] + v["position"]["height"] <= 1080 for v in _visuais(pagina))


def test_executivo_no_estilo_da_previa():
    assert {"HTML Menu Executivo", "HTML Cabeçalho Executivo", "HTML Cartões Executivo",
            "HTML Receita Mensal", "HTML Atraso por Região", "HTML Grupos Top 5"} <= _medidas_html("Executivo")
    for nativo in ("cardVisual", "card", "areaChart", "lineChart", "tableEx", "textbox"):
        assert not _tem_visual("Executivo", nativo), nativo
    assert _tem_visual("Executivo", "slicer")
    assert _tem_visual("Executivo", "pageNavigator")
    assert _dentro_da_pagina("Executivo")


def test_entrega_no_estilo_da_previa():
    assert {"HTML Menu Entrega", "HTML Cabeçalho Entrega", "HTML Cartões Entrega", "HTML Atraso por Região",
            "HTML Excesso por UF", "HTML Pedidos em Risco"} <= _medidas_html("Entrega e risco")
    for nativo in ("cardVisual", "card", "clusteredBarChart", "tableEx", "textbox"):
        assert not _tem_visual("Entrega e risco", nativo), nativo
    assert _tem_visual("Entrega e risco", "slicer") and _tem_visual("Entrega e risco", "pageNavigator")
    assert _dentro_da_pagina("Entrega e risco")


def test_vendedores_no_estilo_da_previa():
    assert {"HTML Menu Vendedores", "HTML Cabeçalho Vendedores", "HTML Cartões Vendedores", "HTML Grupos",
            "HTML Vendedores"} <= _medidas_html("Vendedores")
    for nativo in ("cardVisual", "card", "clusteredBarChart", "tableEx", "textbox"):
        assert not _tem_visual("Vendedores", nativo), nativo
    assert _tem_visual("Vendedores", "slicer") and _tem_visual("Vendedores", "pageNavigator")
    assert _dentro_da_pagina("Vendedores")


def _tem_segmentacao(pagina: str, tabela: str, coluna: str) -> bool:
    for v in _visuais(pagina):
        if v["visual"]["visualType"] != "slicer":
            continue
        for p in v["visual"]["query"]["queryState"]["Values"]["projections"]:
            campo = p["field"].get("Column", {})
            if campo.get("Expression", {}).get("SourceRef", {}).get("Entity") == tabela and campo.get("Property") == coluna:
                return True
    return False


def _indicadores() -> list[dict]:
    pasta = RELATORIO / "definition" / "bookmarks"
    return [_ler(b) for b in pasta.glob("*.bookmark.json")]


def test_dicionario_em_todas_as_paginas():
    for pagina in ("Executivo", "Entrega e risco", "Vendedores"):
        assert "HTML Dicionário" in _medidas_html(pagina), pagina
        assert _tem_segmentacao(pagina, "dicionario_metricas", "Métrica"), pagina
        assert _dentro_da_pagina(pagina), pagina
        # salvar no Desktop com o painel aberto grava o estado aberto: o relatorio deve abrir fechado
        painel = [v for v in _visuais(pagina) if "HTML Dicionário" in json.dumps(v, ensure_ascii=False)
                  or "dicionario_metricas" in json.dumps(v)]
        assert painel and all(v.get("isHidden") for v in painel), pagina


def test_indicadores_do_dicionario_nao_guardam_filtros():
    """Dois por pagina (aberto e fechado), so de exibicao: abrir o dicionario nao pode desfazer o periodo."""
    nomes = {b["displayName"] for b in _indicadores()}
    for pagina in ("Executivo", "Entrega", "Vendedores"):
        assert {f"Dicionário aberto {pagina}", f"Dicionário fechado {pagina}"} <= nomes
    for b in _indicadores():
        if b["displayName"].startswith("Dicionário"):
            assert b["options"].get("suppressData") is True, b["displayName"]


def test_medidas_html_sem_texto_em_degrade():
    """background-clip:text vira um bloco colorido na exportacao para PDF (prints da Etapa 8)."""
    medidas = RELATORIO.parent / "Olist.SemanticModel" / "definition" / "tables" / "_Medidas.tmdl"
    assert "background-clip:text" not in medidas.read_text(encoding="utf-8")


def test_gerador_reproduz_as_medidas_html(tmp_path):
    """Quem editar uma medida HTML direto no TMDL perde a edicao na proxima geracao."""
    import subprocess
    import sys

    relativo = Path("dashboards/powerbi/Olist.SemanticModel/definition/tables/_Medidas.tmdl")
    original = RELATORIO.parents[2] / relativo
    copia = tmp_path / relativo
    copia.parent.mkdir(parents=True)
    copia.write_bytes(original.read_bytes())
    gerador = RELATORIO.parent / "gerar_medidas_html.py"
    r = subprocess.run([sys.executable, str(gerador)], cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert copia.read_bytes() == original.read_bytes()


def test_segmentacoes_suspensas_abrem_no_tema_escuro():
    """Sem cor nos itens, a lista suspensa abre branca com texto claro (ilegivel)."""
    for pagina in _paginas():
        for v in _visuais(pagina):
            objetos = v["visual"].get("objects", {})
            if v["visual"]["visualType"] != "slicer":
                continue
            modo = objetos.get("data", [{}])[0].get("properties", {}).get("mode", {})
            if modo.get("expr", {}).get("Literal", {}).get("Value") != "'Dropdown'":
                continue
            itens = objetos.get("items", [{}])[0].get("properties", {})
            fundo = itens.get("background", {}).get("solid", {}).get("color", {})
            assert fundo.get("expr", {}).get("Literal", {}).get("Value") == "'#17214A'", (pagina, v["name"])


def test_texto_do_banco_entra_escapado_no_html():
    """Coluna concatenada direto no HTML (sem o SUBSTITUTE de & < >) quebra o desenho
    no dia em que um rotulo tiver esses caracteres."""
    import re

    texto = (RELATORIO.parent / "Olist.SemanticModel" / "definition" / "tables" / "_Medidas.tmdl").read_text(encoding="utf-8")
    html = texto[texto.index("/// Menu lateral (molde)"):]
    nua = re.findall(r'&\s+((?:RELATED \( )?\w+\[[^\]]+\](?: \))?)\s+&', html)
    assert not nua, nua


def _rodar_gerador(tmp_path, transformar):
    import subprocess
    import sys

    relativo = Path("dashboards/powerbi/Olist.SemanticModel/definition/tables/_Medidas.tmdl")
    original = (RELATORIO.parents[2] / relativo).read_text(encoding="utf-8")
    copia = tmp_path / relativo
    copia.parent.mkdir(parents=True)
    antes = transformar(original)
    copia.write_text(antes, encoding="utf-8", newline="")
    r = subprocess.run([sys.executable, str(RELATORIO.parent / "gerar_medidas_html.py")], cwd=tmp_path,
                       capture_output=True, text=True)
    return r, antes, copia.read_text(encoding="utf-8")


def test_gerador_nao_apaga_medida_que_nao_e_html(tmp_path):
    """O Desktop poe medida nova no fim da tabela, dentro do trecho que o gerador regrava."""
    nova = "\tmeasure 'Medida Nova' = 1\n\t\tlineageTag: 11111111-2222-3333-4444-555555555555\n\n"
    r, antes, depois = _rodar_gerador(tmp_path, lambda t: t.replace("\tcolumn ", nova + "\tcolumn ", 1))
    assert r.returncode != 0
    assert depois == antes


def test_gerador_nao_copia_etiqueta_da_medida_vizinha(tmp_path):
    import re

    def sem_etiqueta(t):
        # tira o lineageTag so da medida de menu do Executivo
        return re.sub(r"(measure 'HTML Menu Executivo' = [^\n]*\n\t\tdisplayFolder: HTML\r?\n)\t\tlineageTag: [0-9a-f-]+\r?\n",
                      r"\1", t, count=1)

    def por_medida(t):
        blocos = re.split(r"\n\t(?=measure |column )", t)
        return {re.match(r"measure '([^']+)'", b).group(1): (re.findall(r"lineageTag: ([0-9a-f-]+)", b) or [None])[0]
                for b in blocos if b.startswith("measure '")}

    r, antes, depois = _rodar_gerador(tmp_path, sem_etiqueta)
    assert r.returncode == 0, r.stderr
    assert por_medida(antes)["HTML Menu Executivo"] is None
    assert por_medida(depois) == por_medida(antes)
