"""Cliente de modelo: provedor de reserva quando a cota estoura."""
from types import SimpleNamespace

import openai
import pytest

from agente.llm import ClienteLLM, CotaEsgotada, Provedor, provedores_do_ambiente


def _cota():
    return openai.RateLimitError.__new__(openai.RateLimitError)


class _Fabrica:
    """Cria clientes falsos; cada provedor responde o texto ou levanta o erro dado."""

    def __init__(self, comportamento):
        self.comportamento = comportamento
        self.chamadas = []

    def __call__(self, api_key, base_url):
        def criar(**kwargs):
            self.chamadas.append((base_url, kwargs))
            r = self.comportamento[base_url]
            if isinstance(r, BaseException):
                raise r
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=r))])
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=criar)))


A = Provedor("gemini", "http://a", "modelo-a", "chave-a")
B = Provedor("groq", "http://b", "modelo-b", "chave-b")
MSG = [{"role": "user", "content": "oi"}]


def test_usa_o_primeiro_provedor():
    fabrica = _Fabrica({"http://a": "resposta a", "http://b": "resposta b"})
    assert ClienteLLM([A, B], fabrica=fabrica).completar(MSG) == "resposta a"
    assert [c[0] for c in fabrica.chamadas] == ["http://a"]


def test_cota_no_primeiro_usa_o_segundo():
    fabrica = _Fabrica({"http://a": _cota(), "http://b": "resposta b"})
    assert ClienteLLM([A, B], fabrica=fabrica).completar(MSG) == "resposta b"


def test_cota_nos_dois_levanta_cota_esgotada():
    fabrica = _Fabrica({"http://a": _cota(), "http://b": _cota()})
    with pytest.raises(CotaEsgotada):
        ClienteLLM([A, B], fabrica=fabrica).completar(MSG)


def test_json_pede_formato_json():
    fabrica = _Fabrica({"http://a": "{}"})
    ClienteLLM([A], fabrica=fabrica).completar(MSG, json=True)
    kwargs = fabrica.chamadas[0][1]
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["model"] == "modelo-a"


def test_provedores_do_ambiente_pula_quem_nao_tem_chave(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    provedores = provedores_do_ambiente()
    assert [p.nome for p in provedores] == ["gemini"]
