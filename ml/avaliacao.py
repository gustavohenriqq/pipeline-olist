"""Metricas, custo, escolha de limiar, calibracao e PSI.

Tudo devolve tipos nativos do Python (float, int, None), para o relatorio ir
direto para metricas.json.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

GRADE_LIMIAR = np.round(np.arange(0.01, 1.0, 0.01), 2)
EPS_PSI = 1e-4


def custo(y, alerta, custo_acao: float, custo_atraso: float) -> float:
    """Acao em todo pedido marcado mais atraso em todo pedido que atrasou sem alerta."""
    y = np.asarray(y).astype(int)
    alerta = np.asarray(alerta).astype(bool)
    perdidos = int(((y == 1) & ~alerta).sum())
    return float(custo_acao * int(alerta.sum()) + custo_atraso * perdidos)


def escolher_limiar(y, prob, custo_acao: float, custo_atraso: float) -> float:
    """Limiar de menor custo na grade 0,01 a 0,99.

    Empate fica com o maior limiar: mesmo custo com menos alertas e menos
    pedidos incomodados.
    """
    prob = np.asarray(prob)
    melhor, menor = None, None
    for t in GRADE_LIMIAR:
        c = custo(y, prob >= t, custo_acao, custo_atraso)
        if menor is None or c <= menor:
            melhor, menor = float(t), c
    return melhor


def metricas(y, prob, limiar: float, custo_acao: float, custo_atraso: float) -> dict:
    y = np.asarray(y).astype(int)
    prob = np.asarray(prob, dtype=float)
    alerta = prob >= limiar
    n, positivos, alertas = len(y), int(y.sum()), int(alerta.sum())
    acertos = int((alerta & (y == 1)).sum())
    duas_classes = 0 < positivos < n
    return {
        "n": n,
        "taxa_base": float(positivos / n) if n else None,
        # Com uma classe so, PR-AUC e ROC-AUC nao existem (mes sem atraso).
        "pr_auc": float(average_precision_score(y, prob)) if duas_classes else None,
        "roc_auc": float(roc_auc_score(y, prob)) if duas_classes else None,
        "brier": float(np.mean((prob - y) ** 2)) if n else None,
        "limiar": float(limiar),
        "precisao": float(acertos / alertas) if alertas else None,
        "recall": float(acertos / positivos) if positivos else None,
        "alertas_por_mil": float(1000 * alertas / n) if n else None,
        "custo": custo(y, alerta, custo_acao, custo_atraso),
        "custo_nunca": float(custo_atraso * positivos),
        "custo_sempre": float(custo_acao * n),
    }


def sensibilidade(y_val, p_val, y_teste, p_teste, razoes, custo_acao: float) -> list[dict]:
    """Repete a escolha do limiar para outras razoes de custo, com a acao fixa."""
    y_teste = np.asarray(y_teste).astype(int)
    saida = []
    for r in razoes:
        custo_atraso = custo_acao * r
        limiar = escolher_limiar(y_val, p_val, custo_acao, custo_atraso)
        saida.append({
            "razao": f"1:{r}",
            "custo_atraso": float(custo_atraso),
            "limiar": limiar,
            "alertas_por_mil": float(1000 * (np.asarray(p_teste) >= limiar).mean()),
            "custo_teste": custo(y_teste, np.asarray(p_teste) >= limiar, custo_acao, custo_atraso),
            "custo_nunca": float(custo_atraso * y_teste.sum()),
            "custo_sempre": float(custo_acao * len(y_teste)),
        })
    return saida


def calibracao(y, prob, faixas: int = 10) -> list[dict]:
    """Probabilidade media prevista contra taxa real, por decil de probabilidade."""
    df = pd.DataFrame({"y": np.asarray(y).astype(int), "p": np.asarray(prob, dtype=float)})
    df["faixa"] = pd.qcut(df["p"], faixas, labels=False, duplicates="drop")
    g = df.groupby("faixa").agg(prob_media=("p", "mean"), taxa_real=("y", "mean"), n=("y", "size"))
    return [
        {"prob_media": float(r.prob_media), "taxa_real": float(r.taxa_real), "n": int(r.n)}
        for r in g.itertuples()
    ]


def _proporcoes(rotulos: pd.Series, categorias) -> np.ndarray:
    contagem = rotulos.value_counts(normalize=True)
    return np.array([max(float(contagem.get(c, 0.0)), EPS_PSI) for c in categorias])


def psi(referencia: pd.Series, atual: pd.Series, faixas: int = 10) -> float:
    """Indice de estabilidade populacional. Acima de 0,2 e mudanca relevante.

    Numericas: faixas pelos quantis da referencia (bordas repetidas sao
    fundidas, extremos abertos). Categoricas: uma faixa por categoria. Nulo e
    sempre uma faixa propria, porque nulo crescendo tambem e drift.
    """
    if pd.api.types.is_numeric_dtype(referencia) and pd.api.types.is_numeric_dtype(atual):
        ref_valida = referencia.dropna().astype(float)
        bordas = np.unique(np.quantile(ref_valida, np.linspace(0, 1, faixas + 1)[1:-1])) if len(ref_valida) else []
        cortes = np.concatenate([[-np.inf], bordas, [np.inf]])

        def rotular(s):
            r = pd.cut(s.astype(float), cortes, labels=False, include_lowest=True)
            return r.astype("float").fillna(-1).astype(int)
    else:
        def rotular(s):
            return s.astype(object).where(s.notna(), "__nulo__").astype(str)

    r_ref, r_atual = rotular(referencia), rotular(atual)
    categorias = sorted(set(r_ref.unique()) | set(r_atual.unique()), key=str)
    p_ref = _proporcoes(r_ref, categorias)
    p_atual = _proporcoes(r_atual, categorias)
    return float(np.sum((p_atual - p_ref) * np.log(p_atual / p_ref)))
