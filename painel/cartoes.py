"""Cartoes de indicador do painel em HTML: icone, valor e o destaque do ultimo mes.

Todo texto passa por escape; a cor e o icone so entram se forem de uma lista fixa.
"""
from __future__ import annotations

import re
from html import escape

import pandas as pd

from agente.apresentacao import numero_br

CORES = ("menta", "azul", "violeta", "ambar")


def _vazio(valor) -> bool:
    return valor is None or (not isinstance(valor, str) and pd.isna(valor))


def valor_br(valor, tipo: str) -> str:
    """Valor do cartao no formato brasileiro; None ou NaN vira "sem dados"."""
    if _vazio(valor):
        return "sem dados"
    valor = float(valor)
    if tipo == "moeda_compacta":
        for limite, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
            if abs(valor) >= limite:
                return f"R$ {numero_br(valor / limite, 2)} {sufixo}"
        return f"R$ {numero_br(valor, 2)}"
    if tipo == "moeda":
        return f"R$ {numero_br(valor, 2)}"
    if tipo == "inteiro":
        return numero_br(valor, 0)
    if tipo == "pct":
        return f"{numero_br(valor * 100, 1)}%"
    if tipo == "nota":
        return numero_br(valor, 2)
    raise ValueError(f"tipo de valor desconhecido: {tipo}")


def _delta(variacao, taxa: bool, piora_quando_sobe: bool, sem_anterior: bool) -> str:
    if sem_anterior:
        return '<div class="cartao-delta">sem mês anterior</div>'
    if _vazio(variacao):
        return ""
    variacao = float(variacao)
    seta = "▲" if variacao > 0 else "▼" if variacao < 0 else "="
    numero = f"{numero_br(abs(variacao), 1)} pp" if taxa else f"{numero_br(abs(variacao) * 100, 1)}%"
    subiu = variacao > 0
    classe = "" if variacao == 0 else ("piora" if subiu == piora_quando_sobe else "melhora")
    return (f'<div class="cartao-delta {classe}"><b>{seta} {numero}</b> vs. mês anterior</div>')


def cartao(rotulo: str, valor: str, icone: str, cor: str, variacao: float | None = None, *,
           taxa: bool = False, piora_quando_sobe: bool = False, sem_anterior: bool = False) -> str:
    cor = cor if cor in CORES else "menta"
    icone = icone if re.fullmatch(r"[a-z0-9_]+", icone or "") else "insights"
    return (f'<div class="cartao cor-{cor}">'
            f'<div class="cartao-icone"><span>{icone}</span></div>'
            f'<div><div class="cartao-rotulo">{escape(rotulo)}</div>'
            f'<div class="cartao-valor">{escape(valor)}</div>'
            f"{_delta(variacao, taxa, piora_quando_sobe, sem_anterior)}</div></div>")


def linha_de_cartoes(cartoes: list[str]) -> str:
    return '<div class="cartoes">' + "".join(cartoes) + "</div>"
