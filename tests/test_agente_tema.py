"""Paletas do app: clara (padrao) e escura, trocadas pelo botao de tema."""
from agente.tema import PALETAS, css, tema_valido


def test_paleta_clara_com_destaque_menta():
    assert PALETAS["claro"]["destaque"] == "#10B981"
    assert "--destaque: #10B981" in css("claro")


def test_paleta_escura_com_fundo_escuro():
    assert PALETAS["escuro"]["fundo"] == "#0B1220"
    assert "--fundo: #0B1220" in css("escuro")


def test_tema_padrao_e_desconhecido_caem_no_escuro():
    assert tema_valido("roxo") == "escuro"
    assert tema_valido(None) == "escuro"
    assert tema_valido("claro") == "claro"
    assert css("roxo") == css("escuro")


def test_as_duas_paletas_tem_os_mesmos_tokens():
    assert PALETAS["claro"].keys() == PALETAS["escuro"].keys()
