"""Cliente de modelo gratuito, com provedor de reserva quando a cota estoura.

Gemini e Groq aceitam o formato da API da OpenAI, entao um cliente so serve para
os dois: muda a URL, o modelo e a chave. Ordem: Gemini Flash, Gemini Flash-Lite
(mesma chave; a cota gratuita do Gemini e contada por modelo) e Groq, se houver
chave. Cada um so e tentado quando o anterior responde 429 (cota).
"""
from __future__ import annotations

from dataclasses import dataclass

import openai

from agente.config import env


@dataclass(frozen=True)
class Provedor:
    nome: str
    base_url: str
    modelo: str
    chave: str


class CotaEsgotada(Exception):
    """Todos os provedores recusaram por cota."""


def provedores_do_ambiente() -> list[Provedor]:
    url_gemini = env("AGENTE_URL_GEMINI", "https://generativelanguage.googleapis.com/v1beta/openai/")
    candidatos = [
        Provedor("gemini", url_gemini, env("AGENTE_MODELO_GEMINI", "gemini-flash-latest"),
                 env("GEMINI_API_KEY")),
        Provedor("gemini-lite", url_gemini,
                 env("AGENTE_MODELO_GEMINI_LITE", "gemini-flash-lite-latest"),
                 env("GEMINI_API_KEY")),
        Provedor("groq",
                 env("AGENTE_URL_GROQ", "https://api.groq.com/openai/v1"),
                 env("AGENTE_MODELO_GROQ", "llama-3.3-70b-versatile"),
                 env("GROQ_API_KEY")),
    ]
    return [p for p in candidatos if p.chave]


class ClienteLLM:
    def __init__(self, provedores: list[Provedor], fabrica=openai.OpenAI):
        self.provedores = provedores
        self._clientes = [fabrica(api_key=p.chave, base_url=p.base_url) for p in provedores]
        self.ultimo_provedor: str | None = None

    def completar(self, mensagens: list[dict], json: bool = False) -> str:
        extras = {"response_format": {"type": "json_object"}} if json else {}
        for provedor, cliente in zip(self.provedores, self._clientes):
            try:
                resposta = cliente.chat.completions.create(
                    model=provedor.modelo, messages=mensagens, temperature=0, **extras)
            except openai.RateLimitError:
                continue
            self.ultimo_provedor = provedor.nome
            return resposta.choices[0].message.content or ""
        raise CotaEsgotada()
