"""Fluxo do agente com modelo e banco falsos: nenhuma chamada real."""
import json
from datetime import date
from decimal import Decimal

from agente.agente import Turno, responder
from agente.banco import ErroBanco
from agente.llm import CotaEsgotada

ESQUEMA = "### marts.fato_pedidos"


class _LLM:
    """Devolve as respostas na ordem; uma excecao na lista e levantada."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.mensagens = []

    def completar(self, mensagens, json=False):
        self.mensagens.append(mensagens)
        r = self.respostas.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


class _Banco:
    """Executa a partir de uma lista de resultados ou erros, e guarda os SQLs."""

    def __init__(self, *resultados):
        self.resultados = list(resultados)
        self.sqls = []

    def __call__(self, sql):
        self.sqls.append(sql)
        r = self.resultados.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


def _sql(sql, grafico=None):
    return json.dumps({"sql": sql, "grafico": grafico})


def _texto(mensagens):
    return "\n".join(m["content"] for m in mensagens)


CONTAGEM = "SELECT count(*) AS pedidos FROM fato_pedidos"


def test_caminho_feliz():
    llm = _LLM(_sql(CONTAGEM), "Foram 99.441 pedidos.")
    banco = _Banco((["pedidos"], [(99441,)]))
    r = responder("Quantos pedidos?", [], llm, banco, ESQUEMA)
    assert r.tipo == "ok" and r.confirmada
    assert r.texto == "Foram 99.441 pedidos."
    assert "LIMIT 1000" in r.sql
    assert r.linhas == [(99441,)]


def test_numero_inventado_vira_aviso():
    llm = _LLM(_sql(CONTAGEM), "Foram 120 mil pedidos.")
    r = responder("Quantos pedidos?", [], llm, _Banco((["pedidos"], [(99441,)])), ESQUEMA)
    assert r.tipo == "ok" and not r.confirmada
    assert r.texto == "Resposta automática não confirmada; confira a tabela."


def test_erro_do_banco_e_corrigido_na_segunda_tentativa():
    llm = _LLM(_sql("SELECT x FROM fato_pedidos"), _sql(CONTAGEM), "Foram 99.441 pedidos.")
    banco = _Banco(ErroBanco('column "x" does not exist'), (["pedidos"], [(99441,)]))
    r = responder("Quantos pedidos?", [], llm, banco, ESQUEMA)
    assert r.tipo == "ok"
    assert 'column "x" does not exist' in _texto(llm.mensagens[1])


def test_dois_erros_do_banco():
    llm = _LLM(_sql("SELECT x FROM fato_pedidos"), _sql("SELECT y FROM fato_pedidos"))
    banco = _Banco(ErroBanco("x"), ErroBanco("y"))
    r = responder("Quantos pedidos?", [], llm, banco, ESQUEMA)
    assert r.tipo == "erro"
    assert "y" in r.sql


def test_fora_do_escopo_nao_executa():
    llm = _LLM(json.dumps({"fora_do_escopo": "a base não tem custo dos produtos"}))
    banco = _Banco()
    r = responder("Qual a margem de lucro?", [], llm, banco, ESQUEMA)
    assert r.tipo == "fora_do_escopo"
    assert "custo dos produtos" in r.texto
    assert banco.sqls == []


def test_sql_recusado_nao_executa():
    llm = _LLM(_sql("DELETE FROM fato_pedidos"))
    banco = _Banco()
    r = responder("Apague tudo", [], llm, banco, ESQUEMA)
    assert r.tipo == "recusado"
    assert banco.sqls == []


def test_resultado_vazio_nao_chama_o_modelo_de_novo():
    llm = _LLM(_sql("SELECT uf FROM dim_clientes WHERE uf = 'XX'"))
    r = responder("Clientes do XX?", [], llm, _Banco((["uf"], [])), ESQUEMA)
    assert r.tipo == "vazio"
    assert r.texto == "Nenhum registro encontrado para essa pergunta."
    assert len(llm.mensagens) == 1


def test_cota_na_resposta_mostra_tabela():
    llm = _LLM(_sql(CONTAGEM), CotaEsgotada())
    r = responder("Quantos pedidos?", [], llm, _Banco((["pedidos"], [(99441,)])), ESQUEMA)
    assert r.tipo == "ok" and not r.confirmada
    assert r.linhas == [(99441,)] and r.sql


def test_cota_no_sql():
    r = responder("Quantos pedidos?", [], _LLM(CotaEsgotada()), _Banco(), ESQUEMA)
    assert r.tipo == "cota"


def test_historico_leva_so_os_tres_ultimos_turnos():
    historico = [Turno(f"pergunta {i}", f"SELECT {i}") for i in range(5)]
    llm = _LLM(_sql(CONTAGEM), "Foram 99.441 pedidos.")
    responder("e no Nordeste?", historico, llm, _Banco((["pedidos"], [(99441,)])), ESQUEMA)
    prompt = _texto(llm.mensagens[0])
    assert "pergunta 0" not in prompt and "pergunta 1" not in prompt
    assert all(f"pergunta {i}" in prompt for i in (2, 3, 4))


def test_decimal_none_e_data_nao_quebram():
    llm = _LLM(_sql("SELECT data, valor_total, nota_avaliacao FROM fato_pedidos", "linha"),
               "Em 2018-08 a receita foi de R$ 1.003.308,47.")
    linhas = [(date(2018, 8, 1), Decimal("1003308.47"), None),
              (date(2018, 7, 1), Decimal("1058728.03"), 4)]
    r = responder("Receita em agosto de 2018?", [], llm,
                  _Banco((["data", "valor_total", "nota_avaliacao"], linhas)), ESQUEMA)
    assert r.tipo == "ok" and r.confirmada
    assert r.grafico == "linha"


def test_modelo_sobrecarregado_vira_aviso():
    from agente.llm import ModeloIndisponivel
    r = responder("Quantos pedidos?", [], _LLM(ModeloIndisponivel()), _Banco(), ESQUEMA)
    assert r.tipo == "cota"
    assert "sobrecarregado" in r.texto


def test_erro_inesperado_do_provedor_vira_resposta_de_erro():
    r = responder("Quantos pedidos?", [], _LLM(RuntimeError("Gemini respondeu 403")), _Banco(), ESQUEMA)
    assert r.tipo == "erro"


def test_banco_indisponivel_vira_aviso_sem_nova_tentativa():
    from agente.banco import BancoIndisponivel
    banco = _Banco(BancoIndisponivel("conexão perdida"))
    r = responder("Quantos pedidos?", [], _LLM(_sql("SELECT count(*) FROM marts.fato_pedidos")), banco, ESQUEMA)
    assert r.tipo == "banco"
    assert "acordando" in r.texto
    assert len(banco.sqls) == 1


def test_contexto_vai_ao_modelo_mas_nao_a_resposta():
    contexto = "Contexto do painel: página Entrega e risco; período 01/01/2018 a 31/08/2018."
    llm = _LLM(_sql("SELECT count(*) AS pedidos FROM marts.fato_pedidos"), "Foram 10 pedidos.")
    r = responder("Quantos pedidos?", [], llm, _Banco((["pedidos"], [(10,)])), ESQUEMA, contexto=contexto)
    pedido_sql = llm.mensagens[0][-1]["content"]
    assert "período 01/01/2018 a 31/08/2018" in pedido_sql and "Pergunta: Quantos pedidos?" in pedido_sql
    assert "Contexto do painel" not in r.texto


def test_sem_contexto_o_pedido_nao_muda():
    llm = _LLM(_sql("SELECT 1 AS x FROM marts.fato_pedidos"), "x")
    responder("Quantos pedidos?", [], llm, _Banco((["x"], [(1,)])), ESQUEMA)
    assert "Contexto do painel" not in llm.mensagens[0][-1]["content"]
