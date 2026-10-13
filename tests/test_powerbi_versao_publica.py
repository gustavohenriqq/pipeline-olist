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


def _origem_falsa(raiz: Path) -> Path:
    """Copia do script com uma origem minima, para testar destinos perigosos sem risco."""
    powerbi = raiz / "dashboards" / "powerbi"
    (powerbi / "Olist.Report").mkdir(parents=True)
    (powerbi / "Olist.SemanticModel" / "definition").mkdir(parents=True)
    (powerbi / "Olist.SemanticModel" / "definition" / "model.tmdl").write_text("model Model\n", encoding="utf-8")
    (powerbi / "Olist.pbip").write_text("{}", encoding="utf-8")
    shutil.copy(SCRIPT, powerbi / SCRIPT.name)
    (raiz / "nao_apagar.txt").write_text("dado fora do Git", encoding="utf-8")
    return powerbi


def _rodar(script: Path, destino: Path) -> subprocess.CompletedProcess:
    return subprocess.run([SHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                           "-Destino", str(destino)], capture_output=True, text=True, timeout=120)


def test_copia_publica_recusa_destino_que_contem_a_origem(tmp_path):
    powerbi = _origem_falsa(tmp_path)
    for destino in (powerbi.parent, tmp_path):
        r = _rodar(powerbi / SCRIPT.name, destino)
        assert r.returncode != 0, destino
        assert (tmp_path / "nao_apagar.txt").exists()
        assert (powerbi / "Olist.pbip").exists()


def test_copia_publica_nao_apaga_pasta_que_nao_gerou(tmp_path):
    powerbi = _origem_falsa(tmp_path)
    alheia = tmp_path / "outra"
    alheia.mkdir()
    (alheia / "importante.txt").write_text("x", encoding="utf-8")
    r = _rodar(powerbi / SCRIPT.name, alheia)
    assert r.returncode != 0
    assert (alheia / "importante.txt").exists()
    # pasta gerada pelo proprio script pode ser regerada
    nova = tmp_path / "publico"
    assert _rodar(powerbi / SCRIPT.name, nova).returncode == 0
    assert _rodar(powerbi / SCRIPT.name, nova).returncode == 0
