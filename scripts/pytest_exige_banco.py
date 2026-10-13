"""Plugin do pytest para o CI: banco fora do ar vira falha, nao skip.

Os testes de tests/integracao pulam com "Postgres indisponivel" quando o banco
nao responde, para quem roda sem Docker. No CI isso deixava o passo verde com
zero testes executados. Com este plugin:

- skip com o motivo "Postgres indisponivel" vira falha;
- sessao sem nenhum teste aprovado termina com erro (tudo pulado nao e sucesso).

So o CI carrega o plugin, entao rodar local sem banco continua pulando:
    PYTHONPATH=scripts python -m pytest tests/integracao -p pytest_exige_banco
"""
from __future__ import annotations

import pytest

MOTIVO = "Postgres indisponivel"

_aprovados = 0


def _motivo(report) -> str:
    longrepr = report.longrepr
    if isinstance(longrepr, tuple) and len(longrepr) == 3:   # (arquivo, linha, motivo)
        return str(longrepr[2])
    return str(longrepr)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    report = resultado.get_result()
    if report.skipped and MOTIVO in _motivo(report):
        report.outcome = "failed"
        report.longrepr = (f"{MOTIVO} no CI: o teste de integracao pularia e o passo "
                           "ficaria verde sem testar nada. Confira o service do Postgres "
                           "e as variaveis POSTGRES_*.")


def pytest_runtest_logreport(report):
    global _aprovados
    if report.when == "call" and report.passed:
        _aprovados += 1


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    if exitstatus == pytest.ExitCode.OK and _aprovados == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        relator = session.config.pluginmanager.get_plugin("terminalreporter")
        if relator is not None:
            relator.write_line(f"pytest_exige_banco: nenhum teste passou ({MOTIVO}?); "
                               "no CI isso e falha.", red=True)
