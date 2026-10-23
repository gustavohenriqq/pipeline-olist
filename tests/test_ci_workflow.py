"""Regras do .github/workflows/ci.yml que nao podem regredir sem ninguem ver.

1. Os passos de integracao carregam o plugin que transforma "banco fora" em falha.
2. PR que mexe em ingestao, validacao, hooks do dbt ou no proprio CI faz build
   completo e roda a validacao incremental (o state:modified nao enxerga isso).
"""
import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
CI = RAIZ / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def passos():
    dados = yaml.safe_load(CI.read_text(encoding="utf-8"))
    return dados["jobs"]["build-and-test"]["steps"]


def _passo(passos, trecho):
    achados = [p for p in passos if trecho in p.get("name", "")]
    assert len(achados) == 1, f"esperava um passo com '{trecho}' no nome"
    return achados[0]


def _passo_por_id(passos, ident):
    achados = [p for p in passos if p.get("id") == ident]
    assert len(achados) == 1, f"esperava um passo com id '{ident}'"
    return achados[0]


# ---- 1. integracao nao passa com o banco fora ----

def test_todo_pytest_de_integracao_carrega_o_plugin(passos):
    integracao = [p for p in passos if "tests/integracao" in p.get("run", "")
                  and "--ignore=tests/integracao" not in p.get("run", "")]
    assert len(integracao) >= 2
    for passo in integracao:
        assert "-p pytest_exige_banco" in passo["run"], passo["name"]
        assert passo.get("env", {}).get("PYTHONPATH") == "scripts", passo["name"]


def test_plugin_existe_onde_o_ci_procura():
    assert (RAIZ / "scripts" / "pytest_exige_banco.py").is_file()


# ---- 2. gatilhos do build completo e da validacao no PR ----

def _padrao(passos, nome):
    passo = _passo_por_id(passos, "arquivos")
    padrao = passo.get("env", {}).get(nome)
    assert padrao, f"o passo 'arquivos' precisa expor {nome} em env"
    assert f'"${nome}"' in passo["run"], f"o run do passo 'arquivos' nao usa {nome}"
    return re.compile(padrao)


def _macros_dos_hooks():
    """Arquivos de macro chamados por on-run-start/on-run-end do dbt_project.yml."""
    projeto = yaml.safe_load((RAIZ / "dbt" / "dbt_project.yml").read_text(encoding="utf-8"))
    hooks = projeto.get("on-run-start", []) + projeto.get("on-run-end", [])
    nomes = {m for h in hooks for m in re.findall(r"\{\{\s*(\w+)\(", h)}
    arquivos = set()
    for sql in (RAIZ / "dbt" / "macros").glob("*.sql"):
        texto = sql.read_text(encoding="utf-8")
        if any(re.search(rf"macro\s+{n}\s*\(", texto) for n in nomes):
            arquivos.add(f"dbt/macros/{sql.name}")
    assert arquivos, "nenhuma macro de hook encontrada"
    return sorted(arquivos)


CAMINHOS_INFRA = [
    "ingestion/ingest.py",
    "ingestion/config.py",
    "scripts/validate_incremental.py",
    "dbt/dbt_project.yml",
    "dbt/macros/generate_schema_name.sql",
    ".github/workflows/ci.yml",
] + _macros_dos_hooks()


@pytest.mark.parametrize("caminho", CAMINHOS_INFRA)
def test_caminhos_de_infra_disparam_build_completo_e_validacao(passos, caminho):
    assert _padrao(passos, "PADRAO_INFRA").search(caminho), caminho


@pytest.mark.parametrize("caminho", [
    "README.md",
    "docs/confiabilidade.md",
    "ml/treinar.py",
    "dbt/models/marts/dim_produtos.sql",
    "scripts/publicar_marts.py",
])
def test_caminhos_comuns_nao_disparam_build_completo(passos, caminho):
    assert not _padrao(passos, "PADRAO_INFRA").search(caminho), caminho
    assert not _padrao(passos, "PADRAO_PAINEL").search(caminho), caminho


@pytest.mark.parametrize("caminho", ["painel/consultas.py", "agente/app.py",
                                     "tests/integracao/test_painel_numeros.py",
                                     "dashboards/powerbi/conferencia/esperado.sql"])
def test_caminhos_do_painel_continuam_disparando(passos, caminho):
    assert _padrao(passos, "PADRAO_PAINEL").search(caminho), caminho


def _condicao(passo):
    return re.sub(r"\s+", " ", passo.get("if", ""))


def test_build_completo_no_pr_usa_a_saida_completo(passos):
    seletivo = _passo(passos, "dbt build so do que mudou (PR)")
    completo = _passo(passos, "dbt build completo (PR")
    assert "steps.arquivos.outputs.completo != 'sim'" in _condicao(seletivo)
    assert "steps.arquivos.outputs.completo == 'sim'" in _condicao(completo)


def test_build_seletivo_so_roda_teste_com_todos_os_pais_construidos(passos):
    # Sem o cautious, o PR da distancia_pedido quebrou: o fato entrou como
    # ancestral e levou junto testes de relacao com dimensoes nao construidas.
    run = _passo(passos, "dbt build so do que mudou (PR)")["run"]
    assert "--indirect-selection cautious" in run


def test_validacao_roda_quando_infra_muda(passos):
    validar = _passo(passos, "Validar incrementalidade")
    condicao = _condicao(validar)
    assert "github.event_name == 'push'" in condicao
    assert "steps.selecao.outputs.fatos == 'sim'" in condicao
    assert "steps.arquivos.outputs.infra == 'sim'" in condicao


def test_saidas_do_passo_arquivos(passos):
    run = _passo_por_id(passos, "arquivos")["run"]
    for saida in ("painel=sim", "infra=sim", "completo=sim"):
        assert saida in run, saida
