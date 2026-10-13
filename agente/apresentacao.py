"""Apresentacao da resposta no app: texto, nomes e formatos de coluna, grafico.

Separado do app para ser testado sem rodar o Streamlit.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from html import escape
from numbers import Number
from typing import Callable

import altair as alt
import pandas as pd

from agente.grafico import COLUNAS_DE_TEMPO
from agente.tema import PALETAS

# Eixo do valor como no texto da resposta: 8 mi, 500 mil, 0,08.
ROTULO_COMPACTO = (
    "replace(abs(datum.value) >= 1e9 ? format(datum.value / 1e9, '~g') + ' bi'"
    " : abs(datum.value) >= 1e6 ? format(datum.value / 1e6, '~g') + ' mi'"
    " : abs(datum.value) >= 1e3 ? format(datum.value / 1e3, '~g') + ' mil'"
    " : format(datum.value, '~g'), '.', ',')"
)
ROTULOS = {"ano_mes": "Mês", "mes": "Mês", "ano": "Ano", "uf": "UF", "trimestre": "Trimestre",
           "data": "Data", "pct_no_prazo": "% no prazo", "ticket_medio": "Ticket médio",
           "variacao_mensal": "Var. mensal", "prob_atraso": "Prob. de atraso",
           "entrega_prevista": "Entrega prevista", "taxa_atraso_itens": "Taxa de atraso dos itens",
           "receita_itens": "Receita de itens"}


def escapar_markdown(texto: str) -> str:
    """Dois "R$" na mesma frase viram formula no markdown do Streamlit; escapa o cifrao."""
    return texto.replace("$", "\\$")


def rotulo_coluna(nome: str) -> str:
    if nome in ROTULOS:
        return ROTULOS[nome]
    texto = nome.replace("_", " ").strip()
    return texto[:1].upper() + texto[1:]


def _so_numeros(serie: pd.Series) -> bool:
    valores = serie.dropna()
    return bool(len(valores)) and all(isinstance(v, Number) and not isinstance(v, bool) for v in valores)


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Decimal do banco vira float; coluna so de inteiros (ano, contagem) vira inteiro.

    O Postgres devolve ano e contagens como numeric as vezes, e o float resultante
    aparecia como 2016.0 no eixo e 2017.0000000000002 na tabela.
    """
    saida = df.copy()
    for coluna in saida.columns:
        serie = saida[coluna]
        if pd.api.types.is_bool_dtype(serie) or not _so_numeros(serie):
            continue
        serie = serie.astype(float)
        if ((serie - serie.round()).abs().dropna() < 1e-6).all():
            serie = serie.round().astype("Int64")
        saida[coluna] = serie
    return saida


def numero_br(valor: float, casas: int, milhar: bool = True) -> str:
    if pd.isna(valor):
        return ""
    texto = f"{valor:,.{casas}f}" if milhar else f"{valor:.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def _e_taxa(nome: str) -> bool:
    """O prompt pede taxas como fracao de 0 a 1; na tabela elas viram percentual."""
    nome = nome.lower()
    return nome.startswith(("taxa", "percentual", "pct")) or "percentual" in nome


def formatadores(df: pd.DataFrame) -> dict[str, Callable[[float], str]]:
    """Formato brasileiro fixo por coluna, sem depender do idioma do navegador.

    Taxa (nome taxa_/percentual, de 0 a 1) em %; ano e mes sem milhar; contagem com milhar;
    valor com 2 casas; outra fracao (tudo abaixo de 1) com 4.
    """
    saida = {}
    for coluna in df.columns:
        serie = df[coluna]
        if pd.api.types.is_bool_dtype(serie) or not pd.api.types.is_numeric_dtype(serie):
            continue
        valores = serie.dropna()
        if str(coluna).lower().startswith("variacao"):
            # variacao e fracao que pode passar de 1 ou ser negativa (108,70%, -5,20%)
            saida[coluna] = lambda v: "" if pd.isna(v) else numero_br(v * 100, 2) + "%"
            continue
        if _e_taxa(str(coluna)) and len(valores) and valores.between(0, 1).all():
            saida[coluna] = lambda v: "" if pd.isna(v) else numero_br(v * 100, 2) + "%"
            continue
        if str(coluna).lower() in COLUNAS_DE_TEMPO or str(coluna).lower() == "dia":
            casas, milhar = 0, False
        elif pd.api.types.is_integer_dtype(serie):
            casas, milhar = 0, True
        else:
            valores = serie.dropna().abs()
            casas, milhar = (4 if len(valores) and valores.max() < 1 else 2), True
        saida[coluna] = lambda v, c=casas, m=milhar: numero_br(v, c, m)
    return saida


def _uma_linha(texto: str) -> str:
    """Quebra de linha vira espaco: no markdown do Streamlit, uma linha em branco encerra
    o bloco HTML e o resto da tabela aparece como texto solto."""
    return re.sub(r"\s*[\r\n]\s*", " ", texto)


def _celula(valor) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    texto = "" if valor is None or (not isinstance(valor, str) and pd.isna(valor)) else str(valor)
    return escape(_uma_linha(texto)).replace("$", "&#36;")


def tabela_html(df: pd.DataFrame, classe_linha=None) -> str:
    """Tabela do resultado em HTML, para acompanhar o tema (a do Streamlit e um canvas).

    Tudo que vem do banco passa por escape: um rotulo com "<" nao vira HTML.
    `classe_linha(linha) -> str` pinta a linha (ex.: risco alto); so aceita nome de classe simples.
    """
    formatos = formatadores(df)
    # numero alinhado a direita; ano e mes ficam como rotulo, a esquerda
    numericas = {c for c in formatos if str(c).lower() not in COLUNAS_DE_TEMPO | {"dia"}}
    cabecalho = "".join(
        f'<th class="num">{_celula(rotulo_coluna(str(c)))}</th>' if c in numericas
        else f"<th>{_celula(rotulo_coluna(str(c)))}</th>"
        for c in df.columns)
    linhas = []
    for (_, linha), registro in zip(df.iterrows(), df.itertuples(index=False)):
        classe = classe_linha(linha) if classe_linha else ""
        abre = f'<tr class="{classe}">' if re.fullmatch(r"[a-z-]+", classe or "") else "<tr>"
        celulas = "".join(
            f'<td class="num">{_celula(formatos[c](v))}</td>' if c in numericas
            else f"<td>{_celula(formatos[c](v) if c in formatos else v)}</td>"
            for c, v in zip(df.columns, registro))
        linhas.append(f"{abre}{celulas}</tr>")
    return (f'<div class="tabela-resultado"><table><thead><tr>{cabecalho}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def _eixo_e_medidas(df: pd.DataFrame) -> tuple[str, list[str]]:
    eixo = next((c for c in df.columns
                 if str(c).lower() in COLUNAS_DE_TEMPO or not pd.api.types.is_numeric_dtype(df[c])),
                df.columns[0])
    medidas = [c for c in df.columns if c != eixo and pd.api.types.is_numeric_dtype(df[c])]
    return eixo, medidas


def grafico(df: pd.DataFrame, tipo: str, paleta: dict | None = None) -> alt.Chart:
    """Barras ou linha, eixo do valor compacto (2 mi, 4 mi) e sempre a partir do zero."""
    cores = paleta or PALETAS["claro"]
    eixo, medidas = _eixo_e_medidas(df)
    dados = df[[eixo, *medidas]].copy()
    dados[eixo] = dados[eixo].astype(str)
    x = alt.X(f"{eixo}:N", sort=None, title=rotulo_coluna(eixo), axis=alt.Axis(labelAngle=0))
    eixo_y = alt.Axis(labelExpr=ROTULO_COMPACTO)
    escala = alt.Scale(zero=True)
    if len(medidas) == 1:
        if _e_taxa(str(medidas[0])) and dados[medidas[0]].dropna().between(0, 1).all():
            eixo_y = alt.Axis(format=".0%")
        y = alt.Y(f"{medidas[0]}:Q", title=rotulo_coluna(medidas[0]), axis=eixo_y, scale=escala)
        base = alt.Chart(dados).encode(x=x, y=y, tooltip=[eixo, medidas[0]])
        marca = (base.mark_bar(color=cores["destaque"], cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                 if tipo == "barras" else base.mark_line(color=cores["destaque"], point=True))
        return com_cores(marca, cores)
    longo = dados.melt(id_vars=[eixo], value_vars=medidas, var_name="serie", value_name="valor")
    longo["serie"] = longo["serie"].map(rotulo_coluna)
    y = alt.Y("valor:Q", title=None, axis=eixo_y, scale=escala)
    cor = alt.Color("serie:N", title=None, scale=alt.Scale(range=_series(cores)))
    base = alt.Chart(longo).encode(x=x, y=y, color=cor,
                                   tooltip=[eixo, "serie", "valor"])
    marca = base.mark_bar() if tipo == "barras" else base.mark_line(point=True)
    return com_cores(marca, cores)


def _series(cores: dict) -> list[str]:
    return [cores["destaque"], "#60A5FA", "#F59E0B", "#F472B6"]


def com_cores(grafico_: alt.Chart, cores: dict) -> alt.Chart:
    return (grafico_.properties(height=320, background="transparent")
            .configure_axis(labelColor=cores["texto_suave"], titleColor=cores["texto_suave"],
                            gridColor=cores["grade"], domainColor=cores["borda"], tickColor=cores["borda"])
            .configure_legend(labelColor=cores["texto"])
            .configure_view(strokeWidth=0))
