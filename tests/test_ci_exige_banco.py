"""Plugin scripts/pytest_exige_banco.py: no CI, banco fora do ar vira falha.

Os testes de integracao pulam quando o Postgres nao responde, para quem roda sem
Docker. No CI isso deixava o passo verde com zero testes. Aqui cada caso roda um
pytest de verdade, num arquivo temporario, com e sem o plugin.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
MOTIVO = "Postgres indisponivel"

PULA_SEM_BANCO = f'''
import pytest

@pytest.fixture()
def conexao():
    pytest.skip("{MOTIVO}")

def test_le_o_banco(conexao):
    assert True
'''

PULA_NO_CORPO = f'''
import pytest

def test_le_o_banco():
    pytest.skip("{MOTIVO}")
'''

PULA_POR_OUTRO_MOTIVO = '''
import pytest

def test_sem_caso_na_amostra():
    pytest.skip("caso sem valor nesta base")
'''

PASSA_E_PULA = '''
import pytest

def test_passa():
    assert True

def test_sem_caso_na_amostra():
    pytest.skip("caso sem valor nesta base")
'''


def _pytest(tmp_path, codigo, *, plugin):
    arquivo = tmp_path / "test_alvo.py"
    arquivo.write_text(codigo, encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(RAIZ / "scripts"))
    args = [sys.executable, "-m", "pytest", str(arquivo), "-q", "-p", "no:cacheprovider", "-rs"]
    if plugin:
        args += ["-p", "pytest_exige_banco"]
    return subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True)


def test_sem_plugin_banco_fora_continua_skip(tmp_path):
    """Quem roda local sem Docker nao pode ganhar falha."""
    proc = _pytest(tmp_path, PULA_SEM_BANCO, plugin=False)
    assert proc.returncode == 0, proc.stdout
    assert "1 skipped" in proc.stdout


@pytest.mark.parametrize("codigo, resumo", [
    (PULA_SEM_BANCO, "1 error"),    # skip na fixture: o pytest conta como erro de setup
    (PULA_NO_CORPO, "1 failed"),
], ids=["skip_na_fixture", "skip_no_corpo"])
def test_com_plugin_banco_fora_vira_falha(tmp_path, codigo, resumo):
    proc = _pytest(tmp_path, codigo, plugin=True)
    assert proc.returncode == 1, proc.stdout
    assert resumo in proc.stdout
    assert "skipped" not in proc.stdout
    assert MOTIVO in proc.stdout


def test_com_plugin_zero_testes_passando_falha(tmp_path):
    """Tudo pulado por outro motivo tambem nao pode ficar verde."""
    proc = _pytest(tmp_path, PULA_POR_OUTRO_MOTIVO, plugin=True)
    assert proc.returncode != 0, proc.stdout
    assert "nenhum teste passou" in proc.stdout


def test_com_plugin_skip_legitimo_com_teste_passando_fica_verde(tmp_path):
    proc = _pytest(tmp_path, PASSA_E_PULA, plugin=True)
    assert proc.returncode == 0, proc.stdout
    assert "1 passed, 1 skipped" in proc.stdout


@pytest.mark.parametrize("arquivo", sorted((RAIZ / "tests" / "integracao").glob("test_*.py")),
                         ids=lambda p: p.name)
def test_integracao_pula_com_o_motivo_que_o_plugin_reconhece(arquivo):
    """Se a mensagem do skip mudar, o plugin deixaria de reconhecer."""
    assert f'pytest.skip("{MOTIVO}")' in arquivo.read_text(encoding="utf-8")
