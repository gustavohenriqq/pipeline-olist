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


def test_so_com_chave_do_gemini_a_reserva_e_o_flash_lite(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    provedores = provedores_do_ambiente()
    assert [p.nome for p in provedores] == ["gemini", "gemini-lite"]
    assert provedores[0].modelo != provedores[1].modelo
    assert provedores[0].chave == provedores[1].chave == "g"


def test_com_as_duas_chaves_o_groq_fica_por_ultimo(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("GROQ_API_KEY", "q")
    assert [p.nome for p in provedores_do_ambiente()] == ["gemini", "gemini-lite", "groq"]


def test_sem_chave_nenhuma_nao_ha_provedor(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert provedores_do_ambiente() == []


class _Http:
    """Simula a API nativa do Gemini: responde (status, corpo) e guarda as chamadas."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def __call__(self, url, corpo, cabecalhos):
        self.chamadas.append((url, corpo, cabecalhos))
        return self.respostas.pop(0)


def _texto_gemini(texto):
    return 200, {"candidates": [{"content": {"parts": [{"text": texto}]}}]}


G = Provedor("gemini", "http://g/v1beta", "gemini-x", "chave-g", api="gemini")
MSGS = [
    {"role": "system", "content": "regras"},
    {"role": "user", "content": "exemplo"},
    {"role": "assistant", "content": "{}"},
    {"role": "user", "content": "pergunta"},
]


def test_gemini_nativo_monta_a_chamada():
    http = _Http(_texto_gemini('{"sql": "SELECT 1"}'))
    texto = ClienteLLM([G], enviar=http).completar(MSGS, json=True)
    assert texto == '{"sql": "SELECT 1"}'
    url, corpo, cabecalhos = http.chamadas[0]
    assert url == "http://g/v1beta/models/gemini-x:generateContent"
    assert cabecalhos["x-goog-api-key"] == "chave-g"
    assert corpo["systemInstruction"] == {"parts": [{"text": "regras"}]}
    assert [c["role"] for c in corpo["contents"]] == ["user", "model", "user"]
    assert corpo["generationConfig"]["responseMimeType"] == "application/json"
    assert corpo["generationConfig"]["temperature"] == 0


def test_gemini_429_passa_para_o_proximo():
    http = _Http((429, {"error": {"code": 429}}))
    fabrica = _Fabrica({"http://b": "resposta b"})
    assert ClienteLLM([G, B], fabrica=fabrica, enviar=http).completar(MSG) == "resposta b"


def test_gemini_erro_que_nao_e_cota_levanta():
    http = _Http((403, {"error": {"code": 403, "message": "sem permissao"}}))
    with pytest.raises(RuntimeError, match="403"):
        ClienteLLM([G], enviar=http).completar(MSG)


def test_provedores_do_gemini_usam_a_api_nativa(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    assert {p.api for p in provedores_do_ambiente() if p.nome.startswith("gemini")} == {"gemini"}
