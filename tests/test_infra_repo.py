"""Configuracao do repositorio: macros de metadados, devcontainer e .gitignore."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


# ---- Macros de metadados: schema resolvido pelo dbt, nunca escrito a mao ----

def _sql_sem_comentarios(caminho):
    texto = caminho.read_text(encoding="utf-8")
    return re.sub(r"\{#.*?#\}", "", texto, flags=re.S)


def test_metadados_nao_fixam_schema_marts_nem_meta():
    sql = _sql_sem_comentarios(RAIZ / "dbt" / "macros" / "metadados.sql")
    fixos = re.findall(r"(?<![\w.'])(?:marts|meta)\.\w+|schema if not exists (?:marts|meta)\b", sql)
    assert not fixos, f"schema escrito a mao: {fixos}"


def test_metadados_resolvem_schema_pelo_generate_schema_name():
    sql = _sql_sem_comentarios(RAIZ / "dbt" / "macros" / "metadados.sql")
    assert "generate_schema_name(" in sql


# ---- devcontainer: mesmo requirements do app e sem desligar XSRF/CORS ----

@pytest.fixture(scope="module")
def devcontainer():
    texto = (RAIZ / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    sem_comentarios = re.sub(r"^\s*//.*$", "", texto, flags=re.M)   # JSON com comentarios
    return json.loads(sem_comentarios)


def _comando(valor):
    if isinstance(valor, dict):
        return " ".join(_comando(v) for v in valor.values())
    if isinstance(valor, list):
        return " ".join(valor)
    return valor or ""


def test_devcontainer_instala_o_requirements_do_app(devcontainer):
    instalar = _comando(devcontainer.get("updateContentCommand"))
    arquivos = re.findall(r"-r\s+(\S+)", instalar)
    assert arquivos == ["agente/requirements.txt"], arquivos
    assert (RAIZ / "agente" / "requirements.txt").is_file()


def test_devcontainer_nao_instala_streamlit_sem_versao(devcontainer):
    """A versao fixa do agente/requirements.txt nao pode ser trocada por outra."""
    instalar = _comando(devcontainer.get("updateContentCommand"))
    assert not re.search(r"install\s+(--user\s+)?streamlit\b", instalar)


def test_devcontainer_roda_o_app_sem_desligar_protecoes(devcontainer):
    rodar = _comando(devcontainer.get("postAttachCommand"))
    assert "streamlit run agente/app.py" in rodar
    assert "enableXsrfProtection" not in rodar
    assert "enableCORS" not in rodar
    assert (RAIZ / "agente" / "app.py").is_file()


# ---- .gitignore ----

@pytest.mark.skipif(shutil.which("git") is None, reason="git indisponivel")
@pytest.mark.parametrize("caminho", [
    "agente/avaliacao/ultimo_resultado.md",
    ".superpowers/qualquer/arquivo.md",
])
def test_gitignore_cobre(caminho):
    proc = subprocess.run(["git", "check-ignore", "-q", "--no-index", caminho], cwd=RAIZ)
    assert proc.returncode == 0, f"{caminho} nao esta no .gitignore"


@pytest.mark.skipif(shutil.which("git") is None, reason="git indisponivel")
@pytest.mark.parametrize("caminho", [
    "agente/avaliacao/perguntas.yaml",
    "agente/avaliacao/avaliar.py",
])
def test_gitignore_nao_esconde_a_avaliacao_versionada(caminho):
    proc = subprocess.run(["git", "check-ignore", "-q", "--no-index", caminho], cwd=RAIZ)
    assert proc.returncode == 1, f"{caminho} nao deveria estar ignorado"
