"""Ablacao do historico do vendedor (issue 18), so na validacao.

Executar (da raiz, depois do dbt build): python -m ml.ablacao_historico_vendedor

Treina em 2017 e mede em jan a abr/2018 cinco versoes da lista de numericas,
com os hiperparametros do modelo atual fixos para isolar o efeito das colunas.
Nao calcula nada no teste. Grava ml/artefatos/ablacao_historico_vendedor_validacao.json.
"""
from __future__ import annotations

import json

import pandas as pd

import ml.features as F
from ml.avaliacao import metricas
from ml.config import ARTEFATOS, CUSTO_ACAO, CUSTO_ATRASO, conectar
from ml.dados import _ler, carregar_features, separar

PARAMS = {"learning_rate": 0.1, "max_depth": 3, "min_samples_leaf": 20}
TAXA_RELATIVA = "vendedor_taxa_relativa"
VARIANTES = {
    "sem_historico": (),
    "so_contagem": ("vendedor_entregas_hist",),
    "so_taxa": ("vendedor_taxa_atraso_hist",),
    "contagem_e_taxa": ("vendedor_entregas_hist", "vendedor_taxa_atraso_hist"),
    # taxa do vendedor dividida pela taxa geral da mesma data: tira o nivel
    # da plataforma, que muda de um periodo para o outro
    "contagem_e_taxa_relativa": ("vendedor_entregas_hist", TAXA_RELATIVA),
}


def _carregar() -> pd.DataFrame:
    conn = conectar()
    try:
        df = carregar_features(conn)
        geral = _ler(conn, """
            select distinct compra_dia,
                   geral_atrasos::float8 / nullif(geral_entregues, 0) as taxa_geral
            from ml.ml_historico_vendedor""")
    finally:
        conn.close()
    df["compra_dia"] = df["purchased_at"].dt.normalize()
    geral["compra_dia"] = pd.to_datetime(geral["compra_dia"])
    df = df.merge(geral, on="compra_dia", how="left")
    df[TAXA_RELATIVA] = df["vendedor_taxa_atraso_hist"] / df["taxa_geral"]
    return df


def main() -> None:
    conjuntos = separar(_carregar())
    treino, validacao = conjuntos["treino"], conjuntos["validacao"]
    y_tr = treino[F.ALVO].astype(int).to_numpy()
    y_val = validacao[F.ALVO].astype(int).to_numpy()
    originais = F.NUMERICAS, F.PERMITIDAS
    saida = {}
    try:
        for nome, extras in VARIANTES.items():
            # matriz() e os dois modelos leem as listas do modulo
            F.NUMERICAS = originais[0] + extras
            F.PERMITIDAS = F.NUMERICAS + F.CATEGORICAS
            linha = {}
            for rotulo, modelo in (("principal", F.modelo_principal(**PARAMS)),
                                   ("logistica", F.modelo_logistica())):
                modelo.fit(F.matriz(treino), y_tr)
                p = modelo.predict_proba(F.matriz(validacao))[:, 1]
                m = metricas(y_val, p, 0.5, CUSTO_ACAO, CUSTO_ATRASO)
                linha[rotulo] = {k: round(m[k], 4) for k in ("pr_auc", "roc_auc", "brier")}
            saida[nome] = linha
            print(nome, linha, flush=True)
    finally:
        F.NUMERICAS, F.PERMITIDAS = originais
    with open(ARTEFATOS / "ablacao_historico_vendedor_validacao.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
