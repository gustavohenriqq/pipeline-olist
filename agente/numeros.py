"""Checagem anti-invencao: todo numero da resposta escrita precisa estar no resultado.

O modelo escreve a frase; esta funcao confere, sem modelo, se cada numero dela
saiu das linhas que o banco devolveu (ou da propria pergunta e do SQL). E a
defesa contra o modelo "completar" um valor que parece razoavel.

A comparacao e na precisao em que o numero foi escrito, como um leitor arredonda:
"15,79 mi" casa com 15.786.203,57; "659" casa com 658,65; "8.468" nao casa com 8.467.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

_ESCALAS = (
    (r"bilh(?:ão|ao|ões|oes)\b|bi\b", 1e9),
    (r"milh(?:ão|ao|ões|oes)\b|mi\b", 1e6),
    (r"mil\b", 1e3),
)
_NUMERO = re.compile(
    r"(?<![\w/.,])(?<!\d-)"              # nao continua palavra, data ou outro numero
    r"(-?)"                               # sinal (o "-" de 2018-03 e barrado acima)
    r"(\d{1,3}(?:\.\d{3})+(?!\d)|\d+)"   # inteiro, com ou sem ponto de milhar
    r"(?:,(\d+)|\.(\d{1,2}(?!\d)|\d{4,}))?"  # decimais com virgula, ou com ponto (12.5, 0.0812)
    r"(?![\d/\-]|,\d|\.\d)"               # nao e parte de data (2018-03, 01/08)
    r"(\s*%)?"
    r"(?:\s*(" + "|".join(p for p, _ in _ESCALAS) + r"))?",
    re.IGNORECASE,
)


@dataclass
class _Escrito:
    valor: float       # como escrito, com sinal e sem a escala (15.79 em "15,79 mi")
    casas: int         # casas decimais escritas
    escala: float      # 1, 1e3, 1e6 ou 1e9
    percentual: bool


def _ler(texto: str) -> list[_Escrito]:
    achados = []
    # O modelo le o resultado com ponto decimal e as vezes copia assim ("12.5%").
    # Ponto seguido de 3 digitos segue sendo milhar ("1.234").
    for sinal, inteiro, virgula, ponto, pct, escala_txt in _NUMERO.findall(texto):
        decimais = virgula or ponto or ""
        valor = float(sinal + inteiro.replace(".", "") + ("." + decimais if decimais else ""))
        escala = 1.0
        if escala_txt:
            for padrao, fator in _ESCALAS:
                if re.fullmatch(padrao, escala_txt, re.IGNORECASE):
                    escala = fator
                    break
        achados.append(_Escrito(valor, len(decimais), escala, bool(pct)))
    return achados


def extrair_numeros(texto: str) -> list[float]:
    """Numeros do texto, ja com a escala aplicada (percentual fica como escrito)."""
    return [e.valor * e.escala for e in _ler(texto)]


def _numericos(valores) -> list[float]:
    saida = []
    for v in valores:
        if isinstance(v, bool) or v is None or isinstance(v, (date, datetime, str)):
            continue
        if isinstance(v, (int, float, Decimal)):
            saida.append(float(v))
    return saida


def _casa(escrito: _Escrito, candidato: float) -> bool:
    folga = 0.5 * 10 ** (-escrito.casas) + 1e-9
    opcoes = [candidato / escrito.escala]
    if escrito.percentual:
        opcoes.append(candidato * 100)
    # O sinal conta: "-5,2%" nao confere com 5,23%, nem "5,2%" com -5,23%.
    return any(abs(o - escrito.valor) <= folga for o in opcoes)


def _digitos_de_textos(valores) -> list[float]:
    """Sequencias de digitos dentro de textos do resultado (rotulo "Guariba/SP · 4869f7")."""
    return [float(d) for v in valores if isinstance(v, str) for d in re.findall(r"\d+", v)]


def confere(texto: str, valores, extras=()) -> bool:
    """True se todo numero do texto aparece em `valores` (resultado) ou em `extras`."""
    candidatos = _numericos(valores) + _numericos(extras) + _digitos_de_textos(valores)
    return all(any(_casa(e, c) for c in candidatos) for e in _ler(texto))
