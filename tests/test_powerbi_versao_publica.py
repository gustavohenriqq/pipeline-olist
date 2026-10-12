"""Copia publica do PBIP ("Publicar na Web" nao aceita modelo com RLS).

Roda o script de verdade numa pasta temporaria: sem papeis, mesmo modelo e relatorio.
"""
import filecmp
import shutil
import subprocess
from pathlib import Path

import pytest

POWERBI = Path(__file__).resolve().parents[1] / "dashboards" / "powerbi"
SCRIPT = POWERBI / "gerar_versao_publica.ps1"
SHELL = shutil.which("pwsh") or shutil.which("powershell")

pytestmark = pytest.mark.skipif(SHELL is None, reason="sem PowerShell")


def _gerar(destino: Path) -> subprocess.CompletedProcess:
    return subprocess.run([SHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
                           "-Destino", str(destino)], capture_output=True, text=True, timeout=120)


def test_copia_publica_sem_papeis(tmp_path):
    destino = tmp_path / "publico"
    r = _gerar(destino)
    assert r.returncode == 0, r.stdout + r.stderr
    modelo = destino / "Olist.SemanticModel" / "definition"
    assert (destino / "Olist.pbip").exists()
    assert not (modelo / "roles").exists()
    texto = (modelo / "model.tmdl").read_text(encoding="utf-8")
    assert "ref role" not in texto
    assert "ref table dicionario_metricas" in texto
    # o resto do modelo e o relatorio sao copias exatas
    original = POWERBI / "Olist.SemanticModel" / "definition" / "tables"
    iguais, diferentes, erros = filecmp.cmpfiles(original, modelo / "tables",
                                                 [p.name for p in original.iterdir()], shallow=False)
    assert not diferentes and not erros
    assert filecmp.cmp(POWERBI / "Olist.Report" / "definition" / "report.json",
                       destino / "Olist.Report" / "definition" / "report.json", shallow=False)


def test_copia_publica_nao_mexe_no_original(tmp_path):
    antes = sorted(p.name for p in (POWERBI / "Olist.SemanticModel" / "definition" / "roles").iterdir())
    assert _gerar(tmp_path / "publico").returncode == 0
    depois = sorted(p.name for p in (POWERBI / "Olist.SemanticModel" / "definition" / "roles").iterdir())
    assert antes == depois == ["Diretoria.tmdl", "Gerente regional.tmdl", "Vendedor.tmdl"]


def test_copia_publica_recusa_destino_dentro_do_original(tmp_path):
    r = _gerar(POWERBI / "Olist.SemanticModel" / "publico")
    assert r.returncode != 0
    assert not (POWERBI / "Olist.SemanticModel" / "publico").exists()
