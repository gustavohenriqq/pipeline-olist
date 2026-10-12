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
