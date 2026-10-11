"""Avaliacao de acerto do agente com perguntas de resposta conhecida.

Cada pergunta de perguntas.yaml tem um SQL de referencia. O agente responde de
verdade (gasta cota) e o RESULTADO dele e comparado com o do SQL de referencia,
nao o texto do SQL: o mesmo calculo pode ser escrito de varios jeitos.

Uso: python -m agente.avaliacao.avaliar   (banco do .env, chaves GEMINI/GROQ)
Grava a tabela em agente/avaliacao/ultimo_resultado.md.
"""
from __future__ import annotations

import time
import unicodedata
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import yaml

from agente.config import env

PASTA = Path(__file__).resolve().parent


def _celula(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return str(valor).lower()
    if isinstance(valor, (int, float, Decimal)):
        return f"{round(float(valor), 2):.2f}"
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()[:10]
    texto = unicodedata.normalize("NFKD", str(valor))
    return "".join(c for c in texto if not unicodedata.combining(c)).strip().lower()


def _linha(linha) -> tuple:
    return tuple(sorted(_celula(v) for v in linha))


def mesmo_resultado(linhas_a, linhas_b) -> bool:
    """Mesmos valores por linha, sem olhar nome nem ordem de coluna ou de linha."""
    return Counter(_linha(l) for l in linhas_a) == Counter(_linha(l) for l in linhas_b)


def main() -> None:
    from agente.agente import Turno, responder
    from agente.banco import abrir_conexao, executar
    from agente.llm import ClienteLLM, provedores_do_ambiente

    perguntas = yaml.safe_load((PASTA / "perguntas.yaml").read_text(encoding="utf-8"))
    por_id = {p["id"]: p for p in perguntas}
    esquema = (PASTA.parent / "esquema_marts.md").read_text(encoding="utf-8")
    llm = ClienteLLM(provedores_do_ambiente())
    conexao = abrir_conexao()
    pausa = float(env("AGENTE_AVALIACAO_PAUSA", "12"))

    linhas_md = ["| id | tipo | pergunta | esperado | obtido | ok | provedor |", "|---|---|---|---|---|---|---|"]
    acertos: Counter = Counter()
    totais: Counter = Counter()
    for p in perguntas:
        historico = [Turno(por_id[i]["pergunta"], por_id[i]["sql_referencia"]) for i in p.get("contexto") or []]
        r = responder(p["pergunta"], historico, llm, lambda sql: executar(conexao, sql), esquema)
        if p["sql_referencia"] is None:
            esperado, ok = "fora_do_escopo", r.tipo == "fora_do_escopo"
        else:
            _, referencia = executar(conexao, p["sql_referencia"])
            esperado = f"{len(referencia)} linha(s)"
            ok = r.tipo in ("ok", "vazio") and mesmo_resultado(r.linhas, referencia)
        totais[p["tipo"]] += 1
        acertos[p["tipo"]] += ok
        obtido = r.tipo if r.tipo not in ("ok", "vazio") else f"{len(r.linhas)} linha(s)"
        linhas_md.append(f"| {p['id']} | {p['tipo']} | {p['pergunta']} | {esperado} | {obtido} | "
                         f"{'sim' if ok else 'não'} | {llm.ultimo_provedor or '-'} |")
        print(f"[{'ok' if ok else '--'}] {p['id']}: {p['pergunta']}\n      SQL: {r.sql}")
        time.sleep(pausa)

    resumo = [f"- {t}: {acertos[t]}/{totais[t]}" for t in totais]
    texto = "\n".join(["## Resultado", "", *resumo, "", *linhas_md, ""])
    (PASTA / "ultimo_resultado.md").write_text(texto, encoding="utf-8")
    print("\n".join(resumo))


if __name__ == "__main__":
    main()
