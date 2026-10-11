"""Fluxo de uma pergunta: SQL gerado, guarda, execucao, resposta conferida, grafico.

Sem Streamlit aqui: o app so desenha o que esta funcao devolve, e os testes
rodam com modelo e banco falsos.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from agente.banco import BancoIndisponivel, ErroBanco
from agente.config import LINHAS_NA_RESPOSTA, TENTATIVAS_SQL, TURNOS_HISTORICO
from agente.grafico import escolher_grafico
from agente.guarda_sql import SQLRecusado, validar
from agente.llm import CotaEsgotada, ModeloIndisponivel
from agente.numeros import confere, extrair_numeros
from agente.prompts import EXEMPLOS, SISTEMA_RESPOSTA, SISTEMA_SQL

AVISO_NAO_CONFIRMADA = "Resposta automática não confirmada; confira a tabela."
AVISO_SEM_RESPOSTA = "O modelo ficou indisponível antes da resposta escrita; confira a tabela."
COTA = "A cota gratuita do dia acabou. Volte amanhã."
SOBRECARGA = "O modelo está sobrecarregado agora; tente de novo em instantes."
FALHA_MODELO = "Não consegui falar com o modelo agora; tente de novo em instantes."
VAZIO = "Nenhum registro encontrado para essa pergunta."
BANCO_ACORDANDO = "O banco está acordando ou a conexão caiu; tente de novo em alguns segundos."
PEDE_GRAFICO = re.compile(r"gr[aá]fico|evolu|tend[eê]ncia|ao longo", re.IGNORECASE)


@dataclass
class Turno:
    pergunta: str
    sql: str


@dataclass
class Resposta:
    tipo: str  # ok, vazio, fora_do_escopo, recusado, erro, cota, banco
    texto: str
    sql: str | None = None
    colunas: list[str] = field(default_factory=list)
    linhas: list[tuple] = field(default_factory=list)
    grafico: str | None = None
    confirmada: bool = False


def _mensagens_sql(pergunta: str, historico: list[Turno], esquema: str, erro: str | None,
                   sql_anterior: str | None, contexto: str | None = None) -> list[dict]:
    mensagens = [{"role": "system", "content": SISTEMA_SQL.replace("{esquema}", esquema)}]
    for exemplo, sql in EXEMPLOS:
        mensagens.append({"role": "user", "content": exemplo})
        mensagens.append({"role": "assistant", "content": json.dumps({"sql": sql, "grafico": None})})
    pedido = ""
    recentes = historico[-TURNOS_HISTORICO:]
    if recentes:
        pedido += "Conversa até aqui:\n" + "\n".join(
            f'- Pergunta: "{t.pergunta}" (SQL: {t.sql})' for t in recentes) + "\n\n"
    if contexto:
        # Vem do painel (pagina e filtros da tela); so orienta o SQL, nao aparece para quem pergunta.
        pedido += (f"{contexto} Use esse período (e a região, se houver) quando a pergunta "
                   "não disser outro.\n\n")
    pedido += f"Pergunta: {pergunta}"
    if erro:
        pedido += f"\n\nO SQL anterior falhou.\nSQL: {sql_anterior}\nErro do banco: {erro}\nCorrija."
    mensagens.append({"role": "user", "content": pedido})
    return mensagens


def _ler_json(texto: str) -> dict:
    limpo = texto.strip()
    if limpo.startswith("```"):
        limpo = limpo.strip("`")
        limpo = limpo[limpo.find("{"):]
    inicio, fim = limpo.find("{"), limpo.rfind("}")
    if inicio < 0 or fim < 0:
        raise ValueError("resposta do modelo não é JSON")
    return json.loads(limpo[inicio:fim + 1])


def _csv(colunas: list[str], linhas: list[tuple]) -> str:
    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(colunas)
    for linha in linhas[:LINHAS_NA_RESPOSTA]:
        escritor.writerow(["" if v is None else v for v in linha])
    return saida.getvalue()


def _numeros_do_sql(sql: str) -> list[float]:
    return [float(n) for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", sql)]


def responder(pergunta: str, historico: list[Turno], llm, executar: Callable[[str], tuple],
              esquema: str, contexto: str | None = None) -> Resposta:
    erro = sql = None
    for _ in range(TENTATIVAS_SQL):
        try:
            bruto = llm.completar(_mensagens_sql(pergunta, historico, esquema, erro, sql, contexto), json=True)
        except ModeloIndisponivel:
            return Resposta("cota", SOBRECARGA)
        except CotaEsgotada:
            return Resposta("cota", COTA)
        except Exception:  # noqa: BLE001 (erro do provedor nunca vira traceback na tela)
            return Resposta("erro", FALHA_MODELO)
        try:
            dados = _ler_json(bruto)
        except ValueError as e:
            erro = str(e)
            continue
        if dados.get("fora_do_escopo"):
            return Resposta("fora_do_escopo", str(dados["fora_do_escopo"]))
        try:
            sql = validar(str(dados.get("sql", "")))
        except SQLRecusado as e:
            return Resposta("recusado", e.motivo, sql=dados.get("sql"))
        try:
            colunas, linhas = executar(sql)
        except BancoIndisponivel:
            return Resposta("banco", BANCO_ACORDANDO, sql=sql)
        except ErroBanco as e:
            erro = str(e)
            continue
        break
    else:
        return Resposta("erro", f"Não consegui montar uma consulta válida ({erro}).", sql=sql)

    if not linhas:
        return Resposta("vazio", VAZIO, sql=sql, colunas=colunas)

    df = pd.DataFrame(linhas, columns=colunas)
    grafico = escolher_grafico(df, pedido=bool(PEDE_GRAFICO.search(pergunta)),
                               palpite=dados.get("grafico"))
    base = Resposta("ok", "", sql=sql, colunas=colunas, linhas=linhas, grafico=grafico)

    mensagens = [
        {"role": "system", "content": SISTEMA_RESPOSTA},
        {"role": "user", "content": f"Pergunta: {pergunta}\nSQL: {sql}\nResultado (CSV):\n{_csv(colunas, linhas)}"},
    ]
    try:
        texto = llm.completar(mensagens).strip()
    except Exception:  # noqa: BLE001 (sem frase, a tabela e o SQL continuam valendo)
        base.texto = AVISO_SEM_RESPOSTA
        return base

    valores = [v for linha in linhas[:LINHAS_NA_RESPOSTA] for v in linha]
    extras = extrair_numeros(pergunta) + _numeros_do_sql(sql)
    if confere(texto, valores, extras):
        base.texto, base.confirmada = texto, True
    else:
        base.texto = AVISO_NAO_CONFIRMADA
    return base
