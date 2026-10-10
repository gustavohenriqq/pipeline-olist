"""Constantes do agente: o que ele pode ler, limites e provedores de modelo.

Tudo que define o comportamento do agente fica aqui, num lugar so, para que o
app, os testes e a documentacao usem os mesmos numeros.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")

SCHEMA = "marts"
ROLE = "agente_leitura"

# Star schema e previsoes. Fora: OBTs (o modelo misturaria graos), seguranca_bi
# (lista de acessos do Power BI) e atualizacao_dados (lida pelo app, nao pelo modelo).
TABELAS_PERMITIDAS = (
    "fato_pedidos",
    "fato_itens_pedido",
    "dim_clientes",
    "dim_produtos",
    "dim_vendedores",
    "dim_tempo",
    "dim_geolocalizacao",
    "previsao_atraso",
)

LIMITE_LINHAS = 1000
TIMEOUT_MS = 5000
MAX_PERGUNTA = 300
MAX_POR_SESSAO = 20
TURNOS_HISTORICO = 3
LINHAS_NA_RESPOSTA = 50
TENTATIVAS_SQL = 2


def env(nome: str, padrao: str = "") -> str:
    return os.getenv(nome, padrao)
