"""Cliente de modelo gratuito, com provedor de reserva quando a cota estoura.

Ordem: Gemini Flash, Gemini Flash-Lite (mesma chave; a cota gratuita do Gemini e
contada por modelo) e Groq, se houver chave. Cada um so e tentado quando o
anterior responde 429 (cota).

O Gemini e chamado pela API nativa (generateContent): as chaves novas do Google
(formato "AQ.") sao recusadas na rota compativel com a OpenAI. O Groq usa o
formato da OpenAI.
"""
from __future__ import annotations

import json as _json
import urllib.error
import urllib.request
from dataclasses import dataclass

import openai

from agente.config import env


@dataclass(frozen=True)
class Provedor:
    nome: str
    base_url: str
    modelo: str
    chave: str
    api: str = "openai"  # "openai" ou "gemini" (nativa)


class CotaEsgotada(Exception):
    """Todos os provedores recusaram por cota."""


class ModeloIndisponivel(CotaEsgotada):
    """Todos recusaram, e ao menos um por sobrecarga (5xx), nao por cota."""


class _Cota(Exception):
    """Um provedor recusou por cota (429)."""


class _Sobrecarga(Exception):
    """Um provedor esta sobrecarregado (500, 503): tenta o proximo."""


def provedores_do_ambiente() -> list[Provedor]:
    url_gemini = env("AGENTE_URL_GEMINI", "https://generativelanguage.googleapis.com/v1beta")
    candidatos = [
        Provedor("gemini", url_gemini, env("AGENTE_MODELO_GEMINI", "gemini-flash-latest"),
                 env("GEMINI_API_KEY"), api="gemini"),
        Provedor("gemini-lite", url_gemini,
                 env("AGENTE_MODELO_GEMINI_LITE", "gemini-flash-lite-latest"),
                 env("GEMINI_API_KEY"), api="gemini"),
        Provedor("groq",
                 env("AGENTE_URL_GROQ", "https://api.groq.com/openai/v1"),
                 env("AGENTE_MODELO_GROQ", "llama-3.3-70b-versatile"),
                 env("GROQ_API_KEY")),
    ]
    return [p for p in candidatos if p.chave]


def _enviar_http(url: str, corpo: dict, cabecalhos: dict) -> tuple[int, dict]:
    pedido = urllib.request.Request(url, data=_json.dumps(corpo).encode("utf-8"),
                                    headers={"Content-Type": "application/json", **cabecalhos})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as resposta:
            return resposta.status, _json.load(resposta)
    except urllib.error.HTTPError as erro:
        try:
            return erro.code, _json.loads(erro.read().decode("utf-8") or "{}")
        except ValueError:
            return erro.code, {}


def _corpo_gemini(mensagens: list[dict], json: bool) -> dict:
    sistema = "\n\n".join(m["content"] for m in mensagens if m["role"] == "system")
    conteudo = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in mensagens if m["role"] != "system"]
    corpo = {"contents": conteudo, "generationConfig": {"temperature": 0}}
    if sistema:
        corpo["systemInstruction"] = {"parts": [{"text": sistema}]}
    if json:
        corpo["generationConfig"]["responseMimeType"] = "application/json"
    return corpo


class ClienteLLM:
    def __init__(self, provedores: list[Provedor], fabrica=openai.OpenAI, enviar=_enviar_http):
        self.provedores = provedores
        self._enviar = enviar
        self._clientes = {p.nome: fabrica(api_key=p.chave, base_url=p.base_url)
                          for p in provedores if p.api == "openai"}
        self.ultimo_provedor: str | None = None

    def _gemini(self, p: Provedor, mensagens: list[dict], json: bool) -> str:
        url = f"{p.base_url.rstrip('/')}/models/{p.modelo}:generateContent"
        status, dados = self._enviar(url, _corpo_gemini(mensagens, json), {"x-goog-api-key": p.chave})
        if status == 429:
            raise _Cota()
        if status in (500, 502, 503, 504):
            raise _Sobrecarga()
        if status != 200:
            erro = dados[0] if isinstance(dados, list) and dados else dados
            mensagem = (erro.get("error") or {}).get("message", "") if isinstance(erro, dict) else ""
            raise RuntimeError(f"Gemini respondeu {status}: {mensagem}")
        partes = ((dados.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in partes)

    def _openai(self, p: Provedor, mensagens: list[dict], json: bool) -> str:
        extras = {"response_format": {"type": "json_object"}} if json else {}
        try:
            resposta = self._clientes[p.nome].chat.completions.create(
                model=p.modelo, messages=mensagens, temperature=0, **extras)
        except openai.RateLimitError:
            raise _Cota() from None
        except openai.InternalServerError:
            raise _Sobrecarga() from None
        return resposta.choices[0].message.content or ""

    def completar(self, mensagens: list[dict], json: bool = False) -> str:
        sobrecarga = False
        for provedor in self.provedores:
            chamar = self._gemini if provedor.api == "gemini" else self._openai
            try:
                texto = chamar(provedor, mensagens, json)
            except _Cota:
                continue
            except _Sobrecarga:
                sobrecarga = True
                continue
            self.ultimo_provedor = provedor.nome
            return texto
        raise ModeloIndisponivel() if sobrecarga else CotaEsgotada()
