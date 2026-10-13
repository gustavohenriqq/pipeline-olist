"""Filtros do painel: periodo de compra e regiao do cliente.

Ficam num dataclass congelado: e chave do cache das consultas, entao dois filtros
iguais precisam dar o mesmo hash.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, replace
from datetime import date, timedelta

MINIMO = date(2016, 9, 1)
MAXIMO = date(2018, 10, 31)
REGIOES = ("Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul")


@dataclass(frozen=True)
class Filtros:
    inicio: date
    fim: date
    regiao: str | None = None


# Janela padrao do Power BI e do Looker: meses completos com volume.
PADRAO = Filtros(date(2017, 1, 1), date(2018, 8, 31), None)


def mes_referencia(f: Filtros, ultima_venda: date | None = None) -> str:
    """Mes dos destaques: o da ultima venda no periodo (como o Power BI); sem venda, o do fim."""
    return (ultima_venda or f.fim).strftime("%Y-%m")


def mes_anterior(ano_mes: str) -> str:
    ano, mes = (int(p) for p in ano_mes.split("-"))
    return f"{ano - 1}-12" if mes == 1 else f"{ano}-{mes - 1:02d}"


def _fim_do_mes(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def _um_mes_antes(d: date, fim: bool) -> date:
    """Mesmo dia no mes anterior (cortado no fim do mes); fim de mes vira fim de mes."""
    anterior = d.replace(day=1) - timedelta(days=1)  # ultimo dia do mes anterior
    if fim and d == _fim_do_mes(d):
        return anterior
    return anterior.replace(day=min(d.day, anterior.day))


def janela_comparacao(f: Filtros, ultima_venda: date | None = None) -> tuple[date, date, date, date]:
    """(ref_ini, ref_fim, ant_ini, ant_fim) do destaque "contra o mes anterior".

    O mes de referencia e o da ultima venda dentro do periodo ('Mes de Referencia' do
    Power BI); sem ela, o mes do fim. Como o DATEADD: a referencia usa os dias do
    periodo dentro desse mes, e o anterior sao esses mesmos dias um mes antes. Fim em
    15/08 compara 1 a 15 de agosto com 1 a 15 de julho; inicio em 20/07 nao corta o
    julho da comparacao; fim em 30/11/2016 (sem venda em novembro) compara outubro
    inteiro com setembro inteiro.
    """
    mes = ultima_venda if ultima_venda and f.inicio <= ultima_venda <= f.fim else f.fim
    ref_ini, ref_fim = max(f.inicio, mes.replace(day=1)), min(f.fim, _fim_do_mes(mes))
    return ref_ini, ref_fim, _um_mes_antes(ref_ini, fim=False), _um_mes_antes(ref_fim, fim=True)


def _no_intervalo(d: date) -> date:
    return min(max(d, MINIMO), MAXIMO)


def da_selecao(valor, atual: Filtros) -> Filtros:
    """Aplica o retorno do st.date_input; selecao incompleta mantem o periodo atual.

    Enquanto a pessoa escolhe a segunda data, o widget devolve uma data so.
    """
    if not isinstance(valor, (tuple, list)) or len(valor) != 2:
        return atual
    inicio, fim = sorted(_no_intervalo(d) for d in valor)
    return replace(atual, inicio=inicio, fim=fim)


def para_url(f: Filtros) -> dict[str, str]:
    params = {"inicio": f.inicio.isoformat(), "fim": f.fim.isoformat()}
    if f.regiao:
        params["regiao"] = f.regiao
    return params


def da_url(params) -> Filtros:
    """Filtros a partir da URL; qualquer valor invalido cai no padrao."""
    try:
        inicio = date.fromisoformat(params["inicio"])
        fim = date.fromisoformat(params["fim"])
    except (KeyError, TypeError, ValueError):
        return PADRAO
    regiao = params.get("regiao")
    f = da_selecao((inicio, fim), PADRAO)
    return replace(f, regiao=regiao if regiao in REGIOES else None)


def contexto(pagina: str, f: Filtros) -> str:
    """Texto que acompanha a pergunta feita ao lado do painel (nao aparece na tela)."""
    partes = [f"página {pagina}",
              f"período {f.inicio:%d/%m/%Y} a {f.fim:%d/%m/%Y}"]
    if f.regiao:
        partes.append(f"região {f.regiao}")
    return "Contexto do painel: " + "; ".join(partes) + "."
