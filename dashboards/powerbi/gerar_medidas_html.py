"""Gera as medidas HTML (TMDL) da Etapa 8 e regrava o bloco em _Medidas.tmdl.

Uso, da raiz do repositorio:  python dashboards/powerbi/gerar_medidas_html.py
Depois, no Desktop: "Apply external changes" e Otimizar > Atualizar visuais.

Substitui o bloco do primeiro molde ("/// Menu lateral (molde)") ate a coluna da
tabela e preserva o lineageTag que o Desktop gravou em cada medida. Os tamanhos
sao escritos na escala da previa (1280 px) e multiplicados por 1,4 no fim (pagina
de 1920 px). Cores e medidas seguem docs/specs/2026-10-12-powerbi-html-design.md.
"""
import re

ARQ = 'dashboards/powerbi/Olist.SemanticModel/definition/tables/_Medidas.tmdl'
FONTE = "font-family:Segoe UI,sans-serif"
SUAVE, TEXTO, CIANO, VIOLETA, ROSA, MENTA, VERM, AMBAR = (
    "#8E9AC8", "#E8ECFF", "#22D3EE", "#8B5CF6", "#EC4899", "#34D399", "#F87171", "#FBBF24")
BLOCO = ("box-sizing:border-box;background:linear-gradient(160deg,#17214A,#121A3A);"
         "border:1px solid rgba(130,150,255,0.14);border-radius:18px")
CARTAO = "position:relative;overflow:hidden;flex:1;" + BLOCO + ";padding:14px 16px;height:calc(100vh - 6px)"
VAZIO = f"<div style='{FONTE};color:{SUAVE};font-size:13px;padding:18px'>sem dados</div>"


def esc(expr):
    return f'SUBSTITUTE ( SUBSTITUTE ( SUBSTITUTE ( {expr}, "&", "&amp;" ), "<", "&lt;" ), ">", "&gt;" )'


def medida(nome, linhas, doc, oculta=False):
    corpo = "\n".join("\t\t\t" + l for l in linhas)
    props = ("\t\tisHidden\n" if oculta else "") + "\t\tdisplayFolder: HTML\n"
    docs = "".join(f"\t/// {d}\n" for d in doc)
    if len(linhas) == 1:  # o Desktop grava medida de uma linha na mesma linha do nome
        return f"{docs}\tmeasure '{nome}' = {linhas[0]}\n{props}\n"
    return f"{docs}\tmeasure '{nome}' =\n{corpo}\n{props}\n"


def spark(chave, medida_serie, cor):
    """VARs de um mini-grafico de area da medida por mes; deixa o SVG em spark_<chave>."""
    k = chave
    return [
        f'VAR t_{k} = FILTER ( ADDCOLUMNS ( VALUES ( dim_tempo[ano_mes] ), "@v", [{medida_serie}] ), NOT ISBLANK ( [@v] ) )',
        f'VAR n_{k} = COUNTROWS ( t_{k} )',
        f'VAR mx_{k} = MAXX ( t_{k}, [@v] )',
        f'VAR mn_{k} = MINX ( t_{k}, [@v] )',
        f'VAR pts_{k} = CONCATENATEX ( t_{k}, FORMAT ( ( RANKX ( t_{k}, dim_tempo[ano_mes], , ASC ) - 1 ) * 300 / MAX ( n_{k} - 1, 1 ), "0.0", "en-US" ) & "," & FORMAT ( 42 - DIVIDE ( [@v] - mn_{k}, mx_{k} - mn_{k}, 0.5 ) * 34, "0.0", "en-US" ), " L ", dim_tempo[ano_mes], ASC )',
        f'VAR spark_{k} = IF ( n_{k} > 1, "<svg viewBox=\'0 0 300 46\' preserveAspectRatio=\'none\' style=\'position:absolute;left:0;bottom:0;width:100%;height:32px\'><defs><linearGradient id=\'g{k}\' x1=\'0\' y1=\'0\' x2=\'0\' y2=\'1\'><stop offset=\'0\' stop-color=\'{cor}\' stop-opacity=\'0.45\'/><stop offset=\'1\' stop-color=\'{cor}\' stop-opacity=\'0\'/></linearGradient></defs><path d=\'M0,46 L " & pts_{k} & " L300,46 Z\' fill=\'url(#g{k})\'/><path d=\'M" & pts_{k} & "\' fill=\'none\' stroke=\'{cor}\' stroke-width=\'2\'/></svg>" )',
    ]


def delta(chave, medida_delta, fmt, sufixo, piora_quando_sobe=False):
    k = chave
    bom, ruim = (VERM, MENTA) if piora_quando_sobe else (MENTA, VERM)
    return [
        f'VAR d_{k} = [{medida_delta}]',
        f'VAR dt_{k} = IF ( ISBLANK ( d_{k} ), "sem mês anterior", "<b style=\'color:" & IF ( d_{k} >= 0, "{bom}", "{ruim}" ) & "\'>" & IF ( d_{k} >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( d_{k} ), "{fmt}" ) & "{sufixo}</b> vs. mês anterior" )',
    ]


def cartao(rotulo, icone, cor_icone, fundo_icone, valor_var, delta_var=None, spark_var=None):
    d = f' & "<div style=\'font-size:11.5px;color:{SUAVE}\'>" & {delta_var} & "</div>"' if delta_var else ""
    s = f" & {spark_var}" if spark_var else ""
    return (f'"<div style=\'{CARTAO}\'><div style=\'font-size:12px;color:{SUAVE};display:flex;align-items:center;gap:8px\'>'
            f'<span style=\'width:26px;height:26px;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;'
            f'background:{fundo_icone};color:{cor_icone};font-weight:700\'>{icone}</span>{rotulo}</div>'
            f'<div style=\'font-size:25px;font-weight:700;margin:6px 0 2px;color:{TEXTO}\'>" & {valor_var} & "</div>"{d}{s} & "</div>"')


def anel(chave, frac_expr, texto_expr, c1, c2):
    return (f'"<svg width=\'78\' height=\'78\' viewBox=\'0 0 78 78\'><defs><linearGradient id=\'a{chave}\'><stop offset=\'0\' stop-color=\'{c1}\'/>'
            f'<stop offset=\'1\' stop-color=\'{c2}\'/></linearGradient></defs><circle cx=\'39\' cy=\'39\' r=\'31\' fill=\'none\' stroke=\'rgba(130,150,255,0.14)\' stroke-width=\'8\'/>'
            f'<circle cx=\'39\' cy=\'39\' r=\'31\' fill=\'none\' stroke=\'url(#a{chave})\' stroke-width=\'8\' stroke-linecap=\'round\' stroke-dasharray=\'" & FORMAT ( 194.8 * {frac_expr}, "0.0", "en-US" ) & " 195\' transform=\'rotate(-90 39 39)\'/>'
            f'<text x=\'39\' y=\'44\' text-anchor=\'middle\' fill=\'{TEXTO}\' font-size=\'15\' font-weight=\'700\'>" & {texto_expr} & "</text></svg>"')


def cartao_anel(rotulo, chave, frac_expr, texto_expr, c1, c2, delta_var=None):
    """Cartao com o anel a esquerda e o rotulo (e a variacao) a direita."""
    d = f' & "<div style=\'font-size:11.5px;color:{SUAVE};margin-top:6px\'>" & {delta_var} & "</div>"' if delta_var else ""
    return (f'"<div style=\'{CARTAO};display:flex;align-items:center;gap:18px\'>" & '
            + anel(chave, frac_expr, texto_expr, c1, c2)
            + f' & "<div><div style=\'font-size:12px;color:{SUAVE}\'>{rotulo}</div>"{d} & "</div></div>"')


MOEDA_MI = 'IF ( {v} >= 1000000, "R$ " & FORMAT ( {v} / 1000000, "#,0.00" ) & " Mi", "R$ " & FORMAT ( {v}, "#,0.00" ) )'


def ou_sem_dados(v, texto):
    return f'IF ( ISBLANK ( {v} ), "sem dados", {texto} )'


def linha_flex():
    return f'"<div style=\'display:flex;gap:14px;{FONTE};height:100vh;box-sizing:border-box;padding:2px\'>"'


# ---------------------------------------------------------------------------
medidas = []

ICONES = {
    "casa": "M3 12l9-8 9 8M5 10v10h14V10",
    "caminhao": "M3 7h11v9H3zM14 10h4l3 3v3h-7M7 19a2 2 0 100-4 2 2 0 000 4zM17 19a2 2 0 100-4 2 2 0 000 4z",
    "loja": "M4 9l2-5h12l2 5M4 9v11h16V9M4 9h16M9 20v-6h6v6",
    "livro": "M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3zM5 17a3 3 0 013-3h11",
}


def item(n, chave):
    return (f"<div {{A{n}}} style='width:46px;height:46px;border-radius:14px;display:flex;align-items:center;justify-content:center;{{S{n}}}'>"
            f"<svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round'><path d='{ICONES[chave]}'/></svg></div>")


menu = (f"<div style='{FONTE};height:100vh;box-sizing:border-box;background:linear-gradient(180deg,#141C44,#0D1330);"
        "border:1px solid rgba(130,150,255,0.14);border-radius:22px;display:flex;flex-direction:column;align-items:center;padding:18px 0;gap:14px'>"
        f"<div style='width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,{CIANO},{VIOLETA});display:flex;align-items:center;justify-content:center;margin-bottom:10px'>"
        "<svg width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='#06102A' stroke-width='2.6' stroke-linecap='round'><path d='M5 19V11M12 19V5M19 19v-6'/></svg></div>"
        + item(1, "casa") + item(2, "caminhao") + item(3, "loja")
        + "<div style='flex:1'></div>" + item(4, "livro").replace("{A4}", "").replace("{S4}", f"color:{SUAVE}") + "</div>")
medidas.append(medida("HTML Menu Base", [f'"{menu}"'],
                      ["Menu lateral (molde): {A1..3} e {S1..3} marcam o icone da pagina ativa."], oculta=True))
ATIVO = f"background:rgba(34,211,238,0.14);color:{CIANO};box-shadow:inset 3px 0 0 {CIANO}"
for nome, ativo in (("Executivo", 1), ("Entrega", 2), ("Vendedores", 3)):
    expr = "[HTML Menu Base]"
    for n in (1, 2, 3):
        a = "data-ativo='1'" if n == ativo else ""
        s = ATIVO if n == ativo else f"color:{SUAVE}"
        expr = f'SUBSTITUTE ( SUBSTITUTE ( {expr}, "{{A{n}}}", "{a}" ), "{{S{n}}}", "{s}" )'
    medidas.append(medida(f"HTML Menu {nome}", [expr], [f"Menu lateral com a pagina {nome} ativa."]))

# texto em degrade (background-clip:text) sai como bloco colorido na exportacao para PDF
GRAD_TXT = f"color:{CIANO}"
cab = (f"<div style='{FONTE};display:flex;flex-direction:column;justify-content:center;height:100vh;box-sizing:border-box;overflow:hidden'>"
       f"<div style='font-size:26px;font-weight:700;color:{TEXTO};letter-spacing:-0.01em'>{{T}}</div>"
       f"<div style='font-size:12.5px;color:{SUAVE};margin-top:2px'>{{S}}\" & IF ( NOT ISBLANK ( [Rótulo do Destaque] ), \" · \" & [Rótulo do Destaque] ) & \"</div></div>")
medidas.append(medida("HTML Cabeçalho Base", [f'"{cab}"'], ["Cabecalho (molde): {T} titulo, {S} subtitulo."], oculta=True))
for nome, titulo, sub in (
        ("Executivo", f"Visão <span style='{GRAD_TXT}'>executiva</span>", "Receita, volume, prazo e satisfação"),
        ("Entrega", f"Entrega <span style='{GRAD_TXT}'>e risco</span>", "Atraso por região e UF e pedidos em andamento com maior risco previsto"),
        ("Vendedores", f"<span style='{GRAD_TXT}'>Vendedores</span>", "No grão de item: exato para cada vendedor")):
    medidas.append(medida(f"HTML Cabeçalho {nome}",
                          [f'SUBSTITUTE ( SUBSTITUTE ( [HTML Cabeçalho Base], "{{T}}", "{titulo}" ), "{{S}}", "{sub}" )'],
                          [f"Cabecalho da pagina {nome}."]))

# --- Cartoes ----------------------------------------------------------------
v_rec = "VAR v_rec = " + ou_sem_dados("[Receita]", MOEDA_MI.format(v="[Receita]"))
linhas = (spark("rec", "Receita", CIANO) + spark("ped", "Pedidos", VIOLETA) + spark("tic", "Ticket Médio", ROSA)
          + delta("rec", "Δ Receita", "0.0%", "") + delta("ped", "Δ Pedidos", "0.0%", "") + delta("tic", "Δ Ticket Médio", "0.0%", "")
          + delta("pra", "Δ % no Prazo", "0.0", " pp") + delta("not", "Δ Nota Média", "0.00", "")
          + [v_rec,
             "VAR v_ped = " + ou_sem_dados("[Pedidos]", 'FORMAT ( [Pedidos], "#,0" )'),
             "VAR v_tic = " + ou_sem_dados("[Ticket Médio]", '"R$ " & FORMAT ( [Ticket Médio], "#,0.00" )'),
             "VAR v_pra = " + ou_sem_dados("[% no Prazo]", 'FORMAT ( [% no Prazo], "0.0%" )'),
             "VAR v_not = " + ou_sem_dados("[Nota Média]", 'FORMAT ( [Nota Média], "0.00" )'),
             "VAR tem = NOT ISBLANK ( [Receita] )",
             "VAR aneis = \"<div style='flex:1.15;" + BLOCO + ";display:flex;align-items:center;justify-content:space-around;height:calc(100vh - 6px)'>\""
             f" & \"<div style='display:flex;flex-direction:column;align-items:center;gap:3px;font-size:11.5px;color:{SUAVE}'>\" & "
             + anel("pra", "COALESCE ( [% no Prazo], 0 )", "v_pra", CIANO, MENTA) + " & \"% no prazo<span>\" & IF ( tem, dt_pra ) & \"</span></div>\""
             f" & \"<div style='display:flex;flex-direction:column;align-items:center;gap:3px;font-size:11.5px;color:{SUAVE}'>\" & "
             + anel("not", "COALESCE ( [Nota Média], 0 ) / 5", "v_not", VIOLETA, ROSA) + " & \"Nota média<span>\" & IF ( tem, dt_not ) & \"</span></div></div>\"",
             "RETURN",
             linha_flex() + " & "
             + cartao("Receita", "R$", CIANO, "rgba(34,211,238,0.16)", "v_rec", "IF ( tem, dt_rec )", "spark_rec") + " & "
             + cartao("Pedidos", "#", VIOLETA, "rgba(139,92,246,0.18)", "v_ped", "IF ( tem, dt_ped )", "spark_ped") + " & "
             + cartao("Ticket médio", "≈", ROSA, "rgba(236,72,153,0.16)", "v_tic", "IF ( tem, dt_tic )", "spark_tic")
             + " & aneis & \"</div>\""])
medidas.append(medida("HTML Cartões Executivo", linhas,
                      ["Cartoes da visao executiva: receita, pedidos e ticket com mini-grafico; aneis de % no prazo e nota."]))

linhas = (delta("atr", "Δ Taxa de Atraso", "0.0", " pp", piora_quando_sobe=True)
          + ["VAR tem = NOT ISBLANK ( [Taxa de Atraso] )",
             # zero alerta num periodo com pedidos e 0, nao "sem dados" (as medidas de risco devolvem BLANK)
             "VAR tem_ped = NOT ISBLANK ( [Pedidos] )",
             "VAR v_atr = " + ou_sem_dados("[Taxa de Atraso]", 'FORMAT ( [Taxa de Atraso], "0.0%" )'),
             'VAR v_ale = IF ( tem_ped, FORMAT ( [Pedidos em Alerta] + 0, "#,0" ), "sem dados" )',
             "VAR v_ris = IF ( tem_ped, " + MOEDA_MI.format(v="( [Receita em Risco] + 0 )") + ', "sem dados" )',
             "RETURN",
             linha_flex() + " & "
             + cartao_anel("Taxa de atraso", "atr", "COALESCE ( [Taxa de Atraso], 0 )", "v_atr", ROSA, VERM, "IF ( tem, dt_atr )") + " & "
             + cartao("Pedidos em alerta", "◔", VIOLETA, "rgba(139,92,246,0.18)", "v_ale") + " & "
             + cartao("Receita em risco", "R$", CIANO, "rgba(34,211,238,0.16)", "v_ris") + " & \"</div>\""])
medidas.append(medida("HTML Cartões Entrega", linhas,
                      ["Cartoes de entrega e risco: taxa de atraso (subir e piorar), alertas e receita em risco."]))

linhas = (spark("rit", "Receita de Itens", CIANO) + delta("rit", "Δ Receita de Itens", "0.0%", "")
          + ["VAR tem = NOT ISBLANK ( [Receita de Itens] )",
             "VAR v_rit = " + ou_sem_dados("[Receita de Itens]", MOEDA_MI.format(v="[Receita de Itens]")),
             "VAR v_ite = " + ou_sem_dados("[Itens]", 'FORMAT ( [Itens], "#,0" )'),
             "VAR v_tai = " + ou_sem_dados("[Taxa de Atraso dos Itens]", 'FORMAT ( [Taxa de Atraso dos Itens], "0.0%" )'),
             "RETURN",
             linha_flex() + " & "
             + cartao("Receita de itens", "R$", CIANO, "rgba(34,211,238,0.16)", "v_rit", "IF ( tem, dt_rit )", "spark_rit") + " & "
             + cartao("Itens", "#", VIOLETA, "rgba(139,92,246,0.18)", "v_ite") + " & "
             + cartao_anel("Taxa de atraso dos itens", "tai", "COALESCE ( [Taxa de Atraso dos Itens], 0 )", "v_tai", ROSA, VERM)
             + " & \"</div>\""])
medidas.append(medida("HTML Cartões Vendedores", linhas, ["Cartoes da pagina de vendedores."]))

# --- Grafico de receita -------------------------------------------------------
titulo_bloco = lambda t, sub="": (f"<div style='font-size:14px;font-weight:600;color:{TEXTO}'>{t}</div>"
                                  + (f"<div style='font-size:11.5px;color:{SUAVE};margin-top:2px'>{sub}</div>" if sub else ""))
CAIXA = f"<div style='{FONTE};{BLOCO};padding:14px 16px;height:100vh;overflow:hidden'>"
X = 'FORMAT ( IF ( n = 1, 393, 48 + ( RANKX ( t, dim_tempo[ano_mes], , ASC ) - 1 ) * 690 / ( n - 1 ) ), "0.0", "en-US" )'
linhas = [
    'VAR t = FILTER ( ADDCOLUMNS ( VALUES ( dim_tempo[ano_mes] ), "@v", [Receita], "@a", [Receita Ano Anterior] ), NOT ISBLANK ( [@v] ) )',
    'VAR n = COUNTROWS ( t )',
    'VAR mx = MAXX ( t, [@v] )',
    'VAR topo = MAX ( mx, MAXX ( t, [@a] ) ) * 1.08',
    # unidade pelo tamanho: com filtro de regiao a receita mensal fica em milhares
    'VAR div = IF ( topo >= 1000000, 1000000, 1000 )',
    'VAR suf = IF ( div = 1000000, " Mi", " mil" )',
    f'VAR pts = CONCATENATEX ( t, {X} & "," & FORMAT ( 300 - [@v] / topo * 280, "0.0", "en-US" ), " L ", dim_tempo[ano_mes], ASC )',
    'VAR ta = FILTER ( t, NOT ISBLANK ( [@a] ) )',
    f'VAR ptsa = CONCATENATEX ( ta, {X} & "," & FORMAT ( 300 - [@a] / topo * 280, "0.0", "en-US" ), " L ", dim_tempo[ano_mes], ASC )',
    f'VAR pontos = CONCATENATEX ( t, "<circle cx=\'" & {X} & "\' cy=\'" & FORMAT ( 300 - [@v] / topo * 280, "0.0", "en-US" ) & "\' r=\'" & IF ( [@v] = mx, "6", "4" ) & "\' fill=\'" & IF ( [@v] = mx, "{CIANO}", "#0E1430" ) & "\' stroke=\'{VIOLETA}\' stroke-width=\'2.5\'/>", "", dim_tempo[ano_mes], ASC )',
    'VAR pico = TOPN ( 1, t, [@v], DESC, dim_tempo[ano_mes], ASC )',
    'VAR pico_mes = MAXX ( pico, dim_tempo[ano_mes] )',
    f'VAR pico_x = MAXX ( pico, {X} )',
    'VAR pico_txt = IF ( n > 0, FORMAT ( DATEVALUE ( pico_mes & "-01" ), "mmm/yy" ) & ": R$ " & FORMAT ( mx / IF ( mx >= 1000000, 1000000, 1000 ), "#,0.00" ) & IF ( mx >= 1000000, " Mi", " mil" ) )',
    f'VAR rotulos = CONCATENATEX ( FILTER ( t, MOD ( RANKX ( t, dim_tempo[ano_mes], , ASC ) - 1, 2 ) = 0 ), "<text x=\'" & {X} & "\' y=\'318\' text-anchor=\'middle\' fill=\'{SUAVE}\' font-size=\'10.5\'>" & FORMAT ( DATEVALUE ( dim_tempo[ano_mes] & "-01" ), "mm/yy" ) & "</text>", "", dim_tempo[ano_mes], ASC )',
    f'VAR grade = CONCATENATEX ( GENERATESERIES ( 0, 3, 1 ), "<line x1=\'48\' x2=\'750\' y1=\'" & FORMAT ( 300 - [Value] / 3 * 280, "0.0", "en-US" ) & "\' y2=\'" & FORMAT ( 300 - [Value] / 3 * 280, "0.0", "en-US" ) & "\' stroke=\'rgba(130,150,255,0.10)\'/><text x=\'40\' y=\'" & FORMAT ( 304 - [Value] / 3 * 280, "0.0", "en-US" ) & "\' text-anchor=\'end\' fill=\'{SUAVE}\' font-size=\'11\'>" & IF ( [Value] = 0, "0", FORMAT ( topo * [Value] / 3 / div, IF ( div = 1000000, "#,0.0", "#,0" ) ) & suf ) & "</text>", "", [Value], ASC )',
    "RETURN",
    'IF ( n = 0, "' + VAZIO + '", "' + CAIXA + titulo_bloco("Receita por mês e no mesmo mês do ano anterior")
    + f"<div style='display:flex;gap:14px;font-size:11px;color:{SUAVE};margin-top:6px'><span><i style='display:inline-block;width:18px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle;background:linear-gradient(90deg,{CIANO},{VIOLETA})'></i>Receita</span><span><i style='display:inline-block;width:18px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle;background:{ROSA}'></i>Ano anterior</span></div>"
    + "<svg width='100%' height='88%' viewBox='0 0 760 330' preserveAspectRatio='none'><defs>"
    + f"<linearGradient id='ga' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{CIANO}' stop-opacity='0.45'/><stop offset='1' stop-color='{VIOLETA}' stop-opacity='0'/></linearGradient>"
    + f"<linearGradient id='gl' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='{CIANO}'/><stop offset='1' stop-color='{VIOLETA}'/></linearGradient></defs>"
    + '" & grade & rotulos & "" & IF ( n > 1, "<path d=\'M48,300 L " & pts & " L738,300 Z\' fill=\'url(#ga)\'/>" ) & "<path d=\'M" & pts & "\' fill=\'none\' stroke=\'url(#gl)\' stroke-width=\'3\'/>" & IF ( COUNTROWS ( ta ) > 1, "<path d=\'M" & ptsa & "\' fill=\'none\' stroke=\'' + ROSA + '\' stroke-width=\'2\' stroke-dasharray=\'6 5\'/>" ) & pontos & "<text x=\'" & pico_x & "\' y=\'" & FORMAT ( 300 - mx / topo * 280 - 14, "0.0", "en-US" ) & "\' text-anchor=\'middle\' fill=\'' + TEXTO + '\' font-size=\'12\' font-weight=\'700\'>" & pico_txt & "</text></svg></div>" )',
]
medidas.append(medida("HTML Receita Mensal", linhas,
                      ["Receita por mes em area com degrade, ano anterior tracejado e o maior mes em destaque (SVG)."]))

# --- Barras ------------------------------------------------------------------
TRILHO = "flex:1;height:8px;border-radius:6px;background:rgba(130,150,255,0.12);position:relative"
LINHA = f"display:flex;align-items:center;gap:10px;font-size:12px;margin-top:9px;color:{TEXTO}"
linhas = [
    'VAR nac = [Taxa Nacional de Atraso]',
    'VAR t = FILTER ( ADDCOLUMNS ( VALUES ( dim_clientes[regiao] ), "@v", [Taxa de Atraso] ), NOT ISBLANK ( [@v] ) )',
    'VAR esc = MAX ( MAXX ( t, [@v] ), nac ) * 1.1',
    f'VAR linhas = CONCATENATEX ( t, "<div style=\'{LINHA}\'><span style=\'width:96px\'>" & {esc("dim_clientes[regiao]")} & "</span><div style=\'{TRILHO}\'><div style=\'width:" & FORMAT ( [@v] / esc * 100, "0.0", "en-US" ) & "%;height:8px;border-radius:6px;background:" & IF ( [@v] > nac, "linear-gradient(90deg,{VERM},{ROSA})", "linear-gradient(90deg,{CIANO},{MENTA})" ) & "\'></div><div style=\'position:absolute;left:" & FORMAT ( nac / esc * 100, "0.0", "en-US" ) & "%;top:-3px;width:2px;height:14px;background:{AMBAR}\'></div></div><span style=\'width:52px;text-align:right\'>" & FORMAT ( [@v], "0.0%" ) & "</span></div>", "", [@v], DESC )',
    "RETURN",
    'IF ( ISEMPTY ( t ), "' + VAZIO + '", "' + CAIXA + titulo_bloco("Taxa de atraso por região", '" & "Linha: média nacional (" & FORMAT ( nac, "0.0%" ) & ")') + '" & linhas & "</div>" )',
]
medidas.append(medida("HTML Atraso por Região", linhas, ["Taxa de atraso por regiao em barras, com a linha da taxa nacional."]))

linhas = [
    'VAR t = FILTER ( ADDCOLUMNS ( VALUES ( dim_clientes[uf] ), "@v", [Atraso em Excesso] ), NOT ISBLANK ( [@v] ) )',
    'VAR esc = MAX ( MAXX ( t, ABS ( [@v] ) ), 1 )',
    f'VAR linhas = CONCATENATEX ( t, "<div style=\'display:flex;align-items:center;gap:8px;font-size:11.5px;margin-top:4px;color:{TEXTO}\'><span style=\'width:24px\'>" & {esc("dim_clientes[uf]")} & "</span><div style=\'flex:1;height:10px;position:relative\'><div style=\'position:absolute;left:50%;top:-2px;width:1px;height:14px;background:rgba(130,150,255,0.35)\'></div><div style=\'position:absolute;top:0;height:10px;border-radius:4px;left:" & FORMAT ( IF ( [@v] >= 0, 50, 50 - ABS ( [@v] ) / esc * 50 ), "0.0", "en-US" ) & "%;width:" & FORMAT ( ABS ( [@v] ) / esc * 50, "0.0", "en-US" ) & "%;background:" & IF ( [@v] > 0, "linear-gradient(90deg,{ROSA},{VERM})", "linear-gradient(90deg,{MENTA},{CIANO})" ) & "\'></div></div><span style=\'width:46px;text-align:right\'>" & FORMAT ( [@v], "+#,0;-#,0;0" ) & "</span></div>", "", [@v], DESC )',
    "RETURN",
    # 27 UFs nao cabem no bloco: lista com rolagem, senao SP (o maior negativo) some
    'IF ( ISEMPTY ( t ), "' + VAZIO + '", "' + CAIXA + titulo_bloco("Atraso em excesso por UF", "Vermelho: acima do esperado pela taxa nacional (role para ver todas)") + "<div style='height:calc(100vh - 80px);overflow-y:auto;padding-right:4px'>" + '" & linhas & "</div></div>" )',
]
medidas.append(medida("HTML Excesso por UF", linhas, ["Atraso em excesso por UF em barras divergentes (vermelho acima da taxa nacional)."]))


def grupos(top):
    base = 'FILTER ( ADDCOLUMNS ( VALUES ( dim_produtos[categoria_grupo] ), "@v", [Receita de Itens] ), NOT ISBLANK ( [@v] ) )'
    tabela = f'TOPN ( 5, {base}, [@v], DESC, dim_produtos[categoria_grupo], ASC )' if top else base
    titulo = "Receita de itens: 5 maiores grupos" if top else "Receita de itens por grupo de categoria"
    return [
        f'VAR t = {tabela}',
        'VAR mx = MAXX ( t, [@v] )',
        f'VAR linhas = CONCATENATEX ( t, "<div data-grupo=\'1\' style=\'{LINHA}\'><span style=\'width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis\'>" & {esc("dim_produtos[categoria_grupo]")} & "</span><div style=\'{TRILHO}\'><div style=\'width:" & FORMAT ( [@v] / mx * 100, "0.0", "en-US" ) & "%;height:8px;border-radius:6px;background:linear-gradient(90deg,{VIOLETA},{CIANO})\'></div></div><span style=\'width:62px;text-align:right\'>" & FORMAT ( [@v] / IF ( mx >= 1000000, 1000000, 1000 ), "#,0.00" ) & IF ( mx >= 1000000, " Mi", " mil" ) & "</span></div>", "", [@v], DESC, dim_produtos[categoria_grupo], ASC )',
        "RETURN",
        'IF ( ISEMPTY ( t ), "' + VAZIO + '", "' + CAIXA + titulo_bloco(titulo) + '" & linhas & "</div>" )',
    ]


medidas.append(medida("HTML Grupos Top 5", grupos(True), ["Os 5 grupos de categoria com maior receita de itens."]))
medidas.append(medida("HTML Grupos", grupos(False), ["Receita de itens de todos os grupos de categoria."]))

# --- Tabelas -------------------------------------------------------------------
TH = f"padding:8px 10px;color:{SUAVE};font-weight:600;text-align:left;position:sticky;top:0;background:#17214A"
TD = "padding:7px 10px;border-top:1px solid rgba(130,150,255,0.10)"
TABELA = f"<div style='{FONTE};{BLOCO};padding:14px 16px;height:100vh;display:flex;flex-direction:column'>"
ROLAGEM = f"<div style='flex:1;overflow:auto;margin-top:8px'><table style='width:100%;border-collapse:collapse;font-size:12px;color:{TEXTO}'>"
linhas = [
    'VAR t = TOPN ( 50, FILTER ( previsao_atraso, previsao_atraso[conjunto] = "em_andamento" ), previsao_atraso[prob_atraso], DESC, RELATED ( fato_pedidos[pedido_codigo] ), ASC )',
    f'VAR linhas = CONCATENATEX ( t, "<tr style=\'" & IF ( previsao_atraso[prob_atraso] >= 0.4, "background:rgba(248,113,113,0.18)", IF ( previsao_atraso[prob_atraso] >= 0.3, "background:rgba(251,191,36,0.16)" ) ) & "\'><td style=\'{TD}\'>" & {esc("RELATED ( fato_pedidos[pedido_codigo] )")} & "</td><td style=\'{TD}\'>" & FORMAT ( RELATED ( fato_pedidos[data_compra] ), "dd/mm/yyyy" ) & "</td><td style=\'{TD}\'>" & FORMAT ( RELATED ( fato_pedidos[entrega_prevista] ), "dd/mm/yyyy" ) & "</td><td style=\'{TD}\'>" & {esc("RELATED ( dim_clientes[uf] )")} & "</td><td style=\'{TD};text-align:right\'>R$ " & FORMAT ( RELATED ( fato_pedidos[valor_total] ), "#,0.00" ) & "</td><td style=\'{TD};text-align:right;font-weight:600\'>" & FORMAT ( previsao_atraso[prob_atraso], "0.0%" ) & "</td></tr>", "", previsao_atraso[prob_atraso], DESC, RELATED ( fato_pedidos[pedido_codigo] ), ASC )',
    "RETURN",
    'IF ( ISEMPTY ( t ), "' + VAZIO + '", "' + TABELA + titulo_bloco("Pedidos em andamento por probabilidade de atraso", "Os 50 de maior risco comprados no período")
    + ROLAGEM + f"<tr><th style='{TH}'>Pedido</th><th style='{TH}'>Compra</th><th style='{TH}'>Entrega prevista</th><th style='{TH}'>UF</th><th style='{TH};text-align:right'>Valor</th><th style='{TH};text-align:right'>Prob.</th></tr>"
    + '" & linhas & "</table></div></div>" )',
]
medidas.append(medida("HTML Pedidos em Risco", linhas,
                      ["Os 50 pedidos em andamento de maior probabilidade de atraso (vermelho a partir de 40%, ambar de 30%)."]))

linhas = [
    # itens e taxa (com TREATAS) so para os 50 do topo, nao para os ~3 mil vendedores
    'VAR t = ADDCOLUMNS ( TOPN ( 50, FILTER ( ADDCOLUMNS ( VALUES ( dim_vendedores[vendedor_rotulo] ), "@r", [Receita de Itens] ), NOT ISBLANK ( [@r] ) ), [@r], DESC, dim_vendedores[vendedor_rotulo], ASC ), "@i", [Itens], "@t", [Taxa de Atraso dos Itens] )',
    'VAR mx = MAXX ( t, [@r] )',
    f'VAR linhas = CONCATENATEX ( t, "<tr><td style=\'{TD};white-space:nowrap\'>" & {esc("dim_vendedores[vendedor_rotulo]")} & "</td><td style=\'{TD};width:34%\'><div style=\'display:flex;align-items:center;gap:8px\'><div style=\'{TRILHO}\'><div style=\'width:" & FORMAT ( [@r] / mx * 100, "0.0", "en-US" ) & "%;height:8px;border-radius:6px;background:linear-gradient(90deg,{VIOLETA},{CIANO})\'></div></div><span style=\'white-space:nowrap\'>" & FORMAT ( [@r], "#,0.00" ) & "</span></div></td><td style=\'{TD};text-align:right\'>" & FORMAT ( [@i], "#,0" ) & "</td><td style=\'{TD};text-align:right\'>" & FORMAT ( [@t], "0.0%" ) & "</td></tr>", "", [@r], DESC, dim_vendedores[vendedor_rotulo], ASC )',
    "RETURN",
    'IF ( ISEMPTY ( t ), "' + VAZIO + '", "' + TABELA + titulo_bloco("Receita e atraso por vendedor", "Os 50 de maior receita de itens no período")
    + ROLAGEM + f"<tr><th style='{TH}'>Vendedor</th><th style='{TH}'>Receita de itens (R$)</th><th style='{TH};text-align:right'>Itens</th><th style='{TH};text-align:right'>Taxa de atraso</th></tr>"
    + '" & linhas & "</table></div></div>" )',
]
medidas.append(medida("HTML Vendedores", linhas, ["Os 50 vendedores de maior receita de itens, com barra proporcional."]))

# --- Dicionario ------------------------------------------------------------------
ROTULO = f"font-size:10px;letter-spacing:0.06em;text-transform:uppercase;color:{SUAVE};margin-top:8px"
CORPO = f"font-size:12px;line-height:1.45;color:{TEXTO};margin-top:2px"
painel = (f"<div style='{FONTE};{BLOCO};padding:16px 16px;height:100vh;display:flex;flex-direction:column;"
          "box-shadow:0 24px 60px rgba(0,0,0,0.55)'>"
          f"<div style='display:flex;align-items:center;gap:8px'><div style='font-size:16px;font-weight:700;color:{TEXTO}'>"
          f"Dicionário de <span style='{GRAD_TXT}'>métricas</span></div><div style='flex:1'></div>"
          f"<div style='width:26px;height:26px;border-radius:9px;display:flex;align-items:center;justify-content:center;"
          f"background:rgba(130,150,255,0.12);color:{SUAVE};font-size:16px'>×</div></div>"
          f"<div style='font-size:11.5px;color:{SUAVE};margin-top:2px'>Busque e marque até 3 métricas</div>"
          "<div style='height:62px;flex:none'></div><div style='flex:1;overflow:auto'>")
cartao_dic = (f'"<div data-metrica=\'1\' style=\'border:1px solid rgba(130,150,255,0.14);border-radius:14px;padding:11px 13px;margin-top:10px;background:rgba(255,255,255,0.03)\'>'
              f'<div style=\'display:flex;align-items:baseline;gap:8px\'><div style=\'font-size:14px;font-weight:700;color:{TEXTO}\'>" & {esc("dicionario_metricas[Métrica]")} & "</div>'
              f'<div style=\'flex:1\'></div><div style=\'font-size:10px;color:{CIANO}\'>" & {esc("dicionario_metricas[Página]")} & "</div></div>'
              f'<div style=\'{ROTULO}\'>O que é</div><div style=\'{CORPO}\'>" & {esc("dicionario_metricas[O que é]")} & "</div>'
              f'<div style=\'{ROTULO}\'>Cálculo</div><div style=\'{CORPO}\'>" & {esc("dicionario_metricas[Cálculo]")} & "</div>'
              f'<div style=\'{ROTULO}\'>Exemplo</div><div style=\'{CORPO}\'>" & {esc("dicionario_metricas[Exemplo]")} & "</div></div>"')
linhas = [
    'VAR filtrado = ISFILTERED ( dicionario_metricas[Métrica] )',
    'VAR n = COUNTROWS ( dicionario_metricas )',
    'VAR t = TOPN ( 3, dicionario_metricas, dicionario_metricas[Ordem], ASC )',
    f'VAR cartoes = CONCATENATEX ( t, {cartao_dic}, "", dicionario_metricas[Ordem], ASC )',
    f'VAR mais = IF ( n > 3, "<div style=\'font-size:11.5px;color:{AMBAR};margin-top:10px\'>e mais " & ( n - 3 ) & " marcadas: o painel mostra até 3 de cada vez.</div>" )',
    f'VAR pedido = "<div style=\'font-size:12.5px;line-height:1.5;color:{SUAVE};margin-top:12px\'>Escolha uma métrica na busca acima para ver o que ela significa, como é calculada e um exemplo com os números do painel.</div>"',
    "RETURN",
    f'"{painel}" & IF ( NOT filtrado || n = 0, pedido, cartoes & mais ) & "</div></div>"',
]
medidas.append(medida("HTML Dicionário", linhas,
                      ["Painel do dicionario: ate 3 metricas marcadas na segmentacao, sem selecao pede para escolher."]))

# ---------------------------------------------------------------------------
texto = open(ARQ, encoding='utf-8', newline='').read()
crlf = '\r\n' in texto
texto = texto.replace('\r\n', '\n')
# o Desktop grava um lineageTag em cada medida; manter o mesmo evita mudanca a toa.
# Cada medida e lida sozinha: uma sem etiqueta nao pode herdar a da vizinha.
TAGS = {}
for bloco in re.split(r"\n\t(?=measure |column )", texto):
    nome = re.match(r"measure '(HTML [^']+)' =", bloco)
    tag = re.search(r"\n\t\tlineageTag: ([0-9a-f-]+)", bloco)
    if nome and tag:
        TAGS[nome.group(1)] = tag.group(1)
if "measure 'HTML " in texto:
    # regera: tira o bloco anterior (do primeiro molde ate a coluna da tabela)
    inicio = texto.index("\t/// Menu lateral (molde)")
    fim = texto.index("\n\tcolumn ")
    # o Desktop poe medida nova no fim da tabela, dentro deste trecho: nunca apagar
    alheias = [m for m in re.findall(r"\n\tmeasure '?([^'=\n]+?)'? =", texto[inicio - 1:fim]) if not m.startswith("HTML ")]
    if alheias:
        raise SystemExit("Medidas que nao sao HTML no trecho do gerador (mova para antes do molde): " + ", ".join(alheias))
    texto = texto[:inicio].rstrip("\n") + texto[fim:]

# a previa foi desenhada em 1280 px de largura; a pagina do relatorio tem 1920
ESCALA = 1.4


def escalar(m):
    v = float(m.group(1)) * ESCALA
    return f"{v:.1f}".rstrip("0").rstrip(".") + "px"


medidas = [re.sub(r"(\d+(?:\.\d+)?)px", escalar, m).replace("width='78' height='78'", "width='109' height='109'")
           for m in medidas]


def com_tag(m):
    nome = re.search(r"\tmeasure '([^']+)' =", m).group(1)
    return m.rstrip("\n") + f"\n\t\tlineageTag: {TAGS[nome]}\n\n" if nome in TAGS else m


medidas = [com_tag(m) for m in medidas]
bloco = "\n" + "".join(medidas)
i = texto.index("\n\tcolumn ")
texto = texto[:i] + "\n" + bloco.rstrip("\n") + "\n" + texto[i:]
if crlf:
    texto = texto.replace('\n', '\r\n')
open(ARQ, 'w', encoding='utf-8', newline='').write(texto)
print("medidas:", len(medidas))
