"""Leitura das features do Postgres e separacao temporal dos conjuntos."""
from __future__ import annotations

import pandas as pd

from ml.config import FIM, FIM_TREINO, FIM_VALIDACAO, INICIO

# OID do tipo numeric no Postgres: o psycopg2 devolve Decimal, que o
# scikit-learn nao aceita. Essas colunas viram float na leitura.
_NUMERIC = 1700


def _ler(conn, sql: str) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql)
        colunas = [d.name for d in cur.description]
        decimais = [d.name for d in cur.description if d.type_code == _NUMERIC]
        df = pd.DataFrame(cur.fetchall(), columns=colunas)
    for col in decimais:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    return df


def carregar_features(conn) -> pd.DataFrame:
    """Le ml.ml_features_atraso inteira (uma linha por pedido)."""
    df = _ler(conn, "select * from ml.ml_features_atraso")
    df["purchased_at"] = pd.to_datetime(df["purchased_at"])
    df["atrasou"] = df["atrasou"].astype("Int64")
    return df


def carregar_atraso_dias(conn) -> pd.DataFrame:
    """atraso_dias do fato. Uso exclusivo do experimento de vazamento proposital."""
    df = _ler(conn, "select pedido_sk, atraso_dias from marts.fato_pedidos")
    df["atraso_dias"] = pd.to_numeric(df["atraso_dias"], errors="coerce").astype("float64")
    return df


def separar(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Treino, validacao e teste pela data da compra; sem resposta vai para em_andamento.

    Pedidos sem entrega nao tem alvo: nao entram em treino nem avaliacao, mas
    sao justamente os que interessam para a previsao operacional.
    """
    data = df["purchased_at"]
    janela = df[(data >= pd.Timestamp(INICIO)) & (data < pd.Timestamp(FIM))]
    data = janela["purchased_at"]
    rotulado = janela["atrasou"].notna()

    def fatia(mascara):
        return janela[mascara].reset_index(drop=True)

    return {
        "treino": fatia(rotulado & (data < pd.Timestamp(FIM_TREINO))),
        "validacao": fatia(rotulado & (data >= pd.Timestamp(FIM_TREINO)) & (data < pd.Timestamp(FIM_VALIDACAO))),
        "teste": fatia(rotulado & (data >= pd.Timestamp(FIM_VALIDACAO))),
        "em_andamento": fatia(~rotulado),
    }
