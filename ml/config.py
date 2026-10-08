"""Constantes do modelo de atraso: cortes de data, custos, caminhos e conexao.

Tudo que define o experimento fica aqui, num lugar so, para que treino,
inferencia e documentacao usem os mesmos numeros.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import psycopg2

from ingestion.config import PG

# Separacao temporal (fim exclusivo). Treino: 2017. Validacao: jan a abr/2018.
# Teste: mai a ago/2018. Antes de 2017 a coleta e irregular e fica de fora.
INICIO = date(2017, 1, 1)
FIM_TREINO = date(2018, 1, 1)
FIM_VALIDACAO = date(2018, 5, 1)
FIM = date(2018, 9, 1)

# Hipotese de custo (inventada e declarada): acao preventiva por pedido marcado
# contra atraso nao evitado. A sensibilidade varia a razao com a acao fixa.
CUSTO_ACAO = 15.0
CUSTO_ATRASO = 60.0
RAZOES_SENSIBILIDADE = (2, 4, 8)

RANDOM_STATE = 42

ARTEFATOS = Path(__file__).resolve().parent / "artefatos"


def conectar():
    """Conexao com o Postgres local, com as mesmas variaveis do .env da ingestao."""
    return psycopg2.connect(**PG)
