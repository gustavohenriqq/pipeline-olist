"""Cliente de modelo: provedor de reserva quando a cota estoura."""
import urllib.error
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


def test_gemini_sobrecarregado_passa_para_o_proximo():
    http = _Http((503, {"error": {"code": 503, "message": "high demand"}}), _texto_gemini("ok lite"))
    lite = Provedor("gemini-lite", "http://g/v1beta", "gemini-lite-x", "chave-g", api="gemini")
    assert ClienteLLM([G, lite], enviar=http).completar(MSG) == "ok lite"


def test_todos_sobrecarregados_levanta_modelo_indisponivel():
    from agente.llm import ModeloIndisponivel
    http = _Http((503, {}), (500, {}))
    lite = Provedor("gemini-lite", "http://g/v1beta", "gemini-lite-x", "chave-g", api="gemini")
    with pytest.raises(ModeloIndisponivel):
        ClienteLLM([G, lite], enviar=http).completar(MSG)


def _429_gemini(quota_id):
    # formato real da API: QuotaFailure com o quotaId que diz se o limite e por minuto ou por dia
    return 429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota.",
                           "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                        "violations": [{"quotaId": quota_id}]},
                                       {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "37s"}]}}


LITE = Provedor("gemini-lite", "http://g/v1beta", "gemini-lite-x", "chave-g", api="gemini")


def test_limite_por_minuto_nos_dois_nao_e_cota_do_dia():
    from agente.llm import LimitePorMinuto
    http = _Http(_429_gemini("GenerateRequestsPerMinutePerProjectPerModel-FreeTier"),
                 _429_gemini("GenerateRequestsPerMinutePerProjectPerModel-FreeTier"))
    with pytest.raises(LimitePorMinuto):
        ClienteLLM([G, LITE], enviar=http).completar(MSG)


def test_cota_do_dia_nos_dois_continua_cota_esgotada():
    from agente.llm import LimitePorMinuto
    http = _Http(_429_gemini("GenerateRequestsPerDayPerProjectPerModel-FreeTier"),
                 _429_gemini("GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
    with pytest.raises(CotaEsgotada) as erro:
        ClienteLLM([G, LITE], enviar=http).completar(MSG)
    assert not isinstance(erro.value, LimitePorMinuto)


def test_dia_num_e_minuto_no_outro_vale_tentar_de_novo():
    # a reserva so esta no limite do minuto: em instantes ela volta a responder
    from agente.llm import LimitePorMinuto
    http = _Http(_429_gemini("GenerateRequestsPerDayPerProjectPerModel-FreeTier"),
                 _429_gemini("GenerateRequestsPerMinutePerProjectPerModel-FreeTier"))
    with pytest.raises(LimitePorMinuto):
        ClienteLLM([G, LITE], enviar=http).completar(MSG)


def test_limite_por_minuto_do_groq():
    from agente.llm import LimitePorMinuto
    erro = _cota()
    erro.body = {"message": "Rate limit reached for model on requests per minute (RPM): Limit 30. "
                            "Please try again in 2s.", "code": "rate_limit_exceeded"}
    erro.message = "Error code: 429"
    fabrica = _Fabrica({"http://b": erro})
    with pytest.raises(LimitePorMinuto):
        ClienteLLM([B], fabrica=fabrica).completar(MSG)


def test_cota_do_dia_do_groq():
    from agente.llm import LimitePorMinuto
    erro = _cota()
    erro.body = {"message": "Rate limit reached for model on tokens per day (TPD): Limit 100000."}
    erro.message = "Error code: 429"
    with pytest.raises(CotaEsgotada) as capturado:
        ClienteLLM([B], fabrica=_Fabrica({"http://b": erro})).completar(MSG)
    assert not isinstance(capturado.value, LimitePorMinuto)


@pytest.mark.parametrize("falha", [
    urllib.error.URLError("getaddrinfo failed"),
    TimeoutError("The read operation timed out"),
    ConnectionResetError("conexao derrubada"),
])
def test_erro_de_rede_no_gemini_passa_para_o_proximo(falha):
    def enviar(url, corpo, cabecalhos):
        raise falha
    fabrica = _Fabrica({"http://b": "resposta b"})
    cliente = ClienteLLM([G, B], fabrica=fabrica, enviar=enviar)
    assert cliente.completar(MSG) == "resposta b"
    assert cliente.ultimo_provedor == "groq"


def test_erro_de_rede_no_openai_passa_para_o_proximo():
    sem_conexao = openai.APITimeoutError.__new__(openai.APITimeoutError)
    fabrica = _Fabrica({"http://a": sem_conexao, "http://b": "resposta b"})
    assert ClienteLLM([A, B], fabrica=fabrica).completar(MSG) == "resposta b"


def test_rede_fora_em_todos_nao_vira_cota():
    # sem rede em nenhum provedor, a mensagem e "tente de novo", nunca "volte amanha"
    def enviar(url, corpo, cabecalhos):
        raise TimeoutError("timed out")
    with pytest.raises(Exception) as erro:
        ClienteLLM([G, LITE], enviar=enviar).completar(MSG)
    assert not isinstance(erro.value, (CotaEsgotada, TimeoutError))
