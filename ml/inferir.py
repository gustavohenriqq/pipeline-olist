"""Pontua todos os pedidos da janela e grava em marts.previsao_atraso.

Executar (da raiz, depois de python -m ml.treinar): python -m ml.inferir

A tabela e criada vazia pelo dbt (hook on-run-start); aqui so se troca o
conteudo, com TRUNCATE + COPY na mesma transacao: quem le a tabela ve a versao
anterior inteira ou a nova inteira, nunca metade. Rodar duas vezes da o mesmo
numero de linhas.
"""
from __future__ import annotations

import io
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.config import ARTEFATOS, FIM_TREINO, FIM_VALIDACAO, conectar
from ml.dados import carregar_features
from ml.features import matriz

COLUNAS_SAIDA = ("pedido_sk", "prob_atraso", "alerta", "conjunto", "limiar", "modelo_versao", "gerado_em")
TABELA = "marts.previsao_atraso"


def carregar_modelo(caminho: Path) -> dict:
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Modelo nao encontrado em {caminho}. Rode antes: python -m ml.treinar")
    return joblib.load(caminho)


def atribuir_conjunto(df: pd.DataFrame) -> pd.Series:
    """Mesma regra de ml.dados.separar, linha a linha.

    Previsao sobre treino e validacao e otimista (o modelo final viu esses
    pedidos); o dashboard deve olhar so teste e em_andamento.
    """
    data = df["purchased_at"]
    conjunto = np.where(
        data < pd.Timestamp(FIM_TREINO), "treino",
        np.where(data < pd.Timestamp(FIM_VALIDACAO), "validacao", "teste"),
    )
    conjunto = np.where(df["atrasou"].isna().to_numpy(), "em_andamento", conjunto)
    return pd.Series(conjunto, index=df.index, name="conjunto")


def montar_saida(df: pd.DataFrame, prob, limiar: float, versao: str, gerado_em) -> pd.DataFrame:
    prob = np.asarray(prob, dtype=float)
    saida = pd.DataFrame({
        "pedido_sk": df["pedido_sk"].to_numpy(),
        "prob_atraso": prob,
        "alerta": prob >= limiar,
        "conjunto": atribuir_conjunto(df).to_numpy(),
        "limiar": float(limiar),
        "modelo_versao": versao,
        "gerado_em": gerado_em,
    })
    return saida[list(COLUNAS_SAIDA)]


def gravar(conn, saida: pd.DataFrame) -> int:
    """Troca todo o conteudo da tabela numa transacao. Devolve as linhas gravadas."""
    buffer = io.StringIO()
    saida.to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    with conn:  # commit no fim; rollback em qualquer erro
        with conn.cursor() as cur:
            cur.execute(f"truncate {TABELA}")
            cur.copy_expert(
                f"copy {TABELA} ({', '.join(COLUNAS_SAIDA)}) from stdin with (format csv)", buffer,
            )
            cur.execute(f"select count(*) from {TABELA}")
            return cur.fetchone()[0]


def main() -> None:
    artefato = carregar_modelo(ARTEFATOS / "modelo.joblib")
    conn = conectar()
    try:
        df = carregar_features(conn)
        prob = artefato["modelo"].predict_proba(matriz(df))[:, 1]
        saida = montar_saida(df, prob, artefato["limiar"], artefato["versao"], pd.Timestamp.now(tz="UTC"))
        n = gravar(conn, saida)
    finally:
        conn.close()
    resumo = saida.groupby("conjunto")["alerta"].agg(["size", "sum"])
    print(f"{n} previsoes gravadas em {TABELA} (versao {artefato['versao']}, limiar {artefato['limiar']})")
    print(resumo.rename(columns={"size": "pedidos", "sum": "alertas"}).to_string())


if __name__ == "__main__":
    main()
