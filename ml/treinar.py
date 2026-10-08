"""Treino e avaliacao do modelo de atraso.

Executar (da raiz, depois do dbt build): python -m ml.treinar

Ordem: baseline e logistica no treino; grade do gradient boosting escolhida
pela PR-AUC da validacao; limiar escolhido por custo na validacao; teste usado
uma vez so, no fim. Depois: sensibilidade do custo, calibracao, backtest
mensal, drift (PSI) e o experimento de vazamento proposital. O modelo salvo e o
principal retreinado em treino + validacao.
"""
from __future__ import annotations

import json
from datetime import date

import joblib
import numpy as np
import pandas as pd

from ml.avaliacao import calibracao, escolher_limiar, metricas, psi, sensibilidade
from ml.config import ARTEFATOS, CUSTO_ACAO, CUSTO_ATRASO, RAZOES_SENSIBILIDADE, conectar
from ml.dados import carregar_atraso_dias, carregar_features, separar
from ml.features import ALVO, CATEGORICAS, PERMITIDAS, matriz, modelo_logistica, modelo_principal, versao_features

GRADE = [
    {"learning_rate": lr, "max_depth": d, "min_samples_leaf": m}
    for lr in (0.05, 0.1) for d in (3, 6, None) for m in (20, 100)
]
LIMITE_DRIFT = 0.2


def _log(msg: str) -> None:
    print(msg, flush=True)


def ajustar_baseline(treino: pd.DataFrame) -> tuple[dict[str, float], float]:
    """Taxa de atraso do treino por UF do cliente, e a taxa geral."""
    y = treino[ALVO].astype(float)
    tabela = y.groupby(treino["cliente_uf"]).mean().to_dict()
    return {str(k): float(v) for k, v in tabela.items()}, float(y.mean())


def prever_baseline(tabela: dict[str, float], geral: float, df: pd.DataFrame) -> np.ndarray:
    """UF sem historico no treino (ou nula) recebe a taxa geral."""
    return df["cliente_uf"].map(tabela).astype(float).fillna(geral).to_numpy()


def _y(df: pd.DataFrame) -> np.ndarray:
    return df[ALVO].astype(int).to_numpy()


def _prob(modelo, df: pd.DataFrame) -> np.ndarray:
    return modelo.predict_proba(matriz(df))[:, 1]


def _avaliar(y_val, p_val, y_teste, p_teste) -> tuple[float, dict, dict]:
    limiar = escolher_limiar(y_val, p_val, CUSTO_ACAO, CUSTO_ATRASO)
    return (
        limiar,
        metricas(y_val, p_val, limiar, CUSTO_ACAO, CUSTO_ATRASO),
        metricas(y_teste, p_teste, limiar, CUSTO_ACAO, CUSTO_ATRASO),
    )


def _backtest(rotulados: pd.DataFrame, params: dict, limiar: float) -> list[dict]:
    """Cada mes de 2018 avaliado por um modelo treinado so com o passado."""
    saida = []
    for inicio in pd.date_range("2018-01-01", "2018-08-01", freq="MS"):
        fim = inicio + pd.offsets.MonthBegin(1)
        passado = rotulados[rotulados["purchased_at"] < inicio]
        mes = rotulados[(rotulados["purchased_at"] >= inicio) & (rotulados["purchased_at"] < fim)]
        if mes.empty or passado[ALVO].nunique() < 2:
            continue
        modelo = modelo_principal(**params).fit(matriz(passado), _y(passado))
        m = metricas(_y(mes), _prob(modelo, mes), limiar, CUSTO_ACAO, CUSTO_ATRASO)
        saida.append({
            "mes": inicio.strftime("%Y-%m"), "n_treino": len(passado), "n": m["n"],
            "taxa_base": m["taxa_base"], "pr_auc": m["pr_auc"], "roc_auc": m["roc_auc"],
            "custo": m["custo"], "custo_nunca": m["custo_nunca"], "custo_sempre": m["custo_sempre"],
        })
        _log(f"  backtest {saida[-1]['mes']}: n={m['n']} taxa={m['taxa_base']:.3f} pr_auc={m['pr_auc']}")
    return saida


def _drift(referencia: pd.DataFrame, atual: pd.DataFrame) -> dict | None:
    if atual.empty:
        return None
    x_ref, x_atual = matriz(referencia), matriz(atual)
    saida = {}
    for col in PERMITIDAS:
        valor = psi(x_ref[col], x_atual[col])
        saida[col] = {"psi": valor, "alerta_drift": bool(valor > LIMITE_DRIFT)}
    return saida


def _sanidade(treino, validacao, atraso_dias: pd.DataFrame, params: dict) -> dict:
    """Vazamento proposital: o mesmo modelo com atraso_dias (o desfecho) como feature.

    Serve so para mostrar no documento o que o vazamento produz. Nao e salvo.
    """
    def com_vazamento(df):
        x = matriz(df)
        x["atraso_dias"] = df[["pedido_sk"]].merge(atraso_dias, on="pedido_sk", how="left")["atraso_dias"].to_numpy()
        return x

    modelo = modelo_principal(**params)
    # A coluna extra entra no fim, depois das numericas: mascara com um False a mais.
    mascara = list(modelo.named_steps["modelo"].categorical_features) + [False]
    modelo.set_params(modelo__categorical_features=mascara)
    modelo.fit(com_vazamento(treino), _y(treino))
    p = modelo.predict_proba(com_vazamento(validacao))[:, 1]
    m = metricas(_y(validacao), p, 0.5, CUSTO_ACAO, CUSTO_ATRASO)
    return {"feature_vazada": "atraso_dias", "roc_auc": m["roc_auc"], "pr_auc": m["pr_auc"]}


def executar(conjuntos: dict[str, pd.DataFrame], atraso_dias: pd.DataFrame | None = None, grade=None) -> dict:
    grade = GRADE if grade is None else grade
    treino, validacao, teste = conjuntos["treino"], conjuntos["validacao"], conjuntos["teste"]
    em_andamento = conjuntos["em_andamento"]
    y_tr, y_val, y_te = _y(treino), _y(validacao), _y(teste)

    _log("baseline e logistica")
    tabela, geral = ajustar_baseline(treino)
    lim_base, val_base, te_base = _avaliar(
        y_val, prever_baseline(tabela, geral, validacao), y_te, prever_baseline(tabela, geral, teste))
    logistica = modelo_logistica().fit(matriz(treino), y_tr)
    lim_log, val_log, te_log = _avaliar(y_val, _prob(logistica, validacao), y_te, _prob(logistica, teste))

    _log(f"grade do gradient boosting ({len(grade)} combinacoes)")
    selecao, melhor = [], None
    for params in grade:
        modelo = modelo_principal(**params).fit(matriz(treino), y_tr)
        p_val = _prob(modelo, validacao)
        pr = metricas(y_val, p_val, 0.5, CUSTO_ACAO, CUSTO_ATRASO)["pr_auc"]
        selecao.append({"params": params, "pr_auc_validacao": pr})
        _log(f"  {params} pr_auc_validacao={pr}")
        if melhor is None or (pr or 0) > (melhor[0] or 0):
            melhor = (pr, params, modelo, p_val)
    _, params, principal, p_val = melhor

    p_te = _prob(principal, teste)
    limiar, val_pri, te_pri = _avaliar(y_val, p_val, y_te, p_te)
    _log(f"escolhido {params}, limiar {limiar}")

    rotulados = pd.concat([treino, validacao, teste], ignore_index=True)
    _log("backtest mensal")
    backtest = _backtest(rotulados, params, limiar)

    _log("drift e sanidade")
    drift = {
        "treino_vs_teste": _drift(treino, teste),
        "treino_vs_em_andamento": _drift(treino, em_andamento),
    }
    sanidade = _sanidade(treino, validacao, atraso_dias, params) if atraso_dias is not None else None

    _log("modelo final (treino + validacao)")
    base_final = pd.concat([treino, validacao], ignore_index=True)
    modelo_final = modelo_principal(**params).fit(matriz(base_final), _y(base_final))

    relatorio = {
        "versao": f"{date.today():%Y%m%d}-{versao_features()}",
        "gerado_em": date.today().isoformat(),
        "features": list(PERMITIDAS),
        "categoricas": list(CATEGORICAS),
        "n": {k: len(v) for k, v in conjuntos.items()},
        "custos": {"acao": CUSTO_ACAO, "atraso": CUSTO_ATRASO},
        "params": params,
        "limiar": limiar,
        "limiares": {"baseline": lim_base, "logistica": lim_log, "principal": limiar},
        "selecao": selecao,
        "validacao": {"baseline": val_base, "logistica": val_log, "principal": val_pri},
        "teste": {"baseline": te_base, "logistica": te_log, "principal": te_pri},
        "sensibilidade": sensibilidade(y_val, p_val, y_te, p_te, RAZOES_SENSIBILIDADE, CUSTO_ACAO),
        "calibracao": calibracao(y_te, p_te),
        "backtest": backtest,
        "drift": drift,
        "sanidade": sanidade,
    }
    return {"limiar": limiar, "params": params, "modelo_final": modelo_final, "relatorio": relatorio}


def _resumo(rel: dict) -> None:
    _log(f"\nversao {rel['versao']}  n={rel['n']}")
    _log(f"params {rel['params']}  limiar {rel['limiar']}")
    for nome, m in rel["teste"].items():
        _log(f"teste {nome:10s} pr_auc={m['pr_auc']:.4f} roc_auc={m['roc_auc']:.4f} "
             f"custo={m['custo']:.0f} nunca={m['custo_nunca']:.0f} sempre={m['custo_sempre']:.0f}")
    if rel["sanidade"]:
        _log(f"sanidade (com atraso_dias): roc_auc={rel['sanidade']['roc_auc']:.4f}")
    em_andamento = rel["drift"]["treino_vs_em_andamento"]
    if em_andamento:
        _log(f"psi prazo_prometido_dias treino x em_andamento: {em_andamento['prazo_prometido_dias']['psi']:.4f}")


def main() -> None:
    conn = conectar()
    try:
        df = carregar_features(conn)
        atraso_dias = carregar_atraso_dias(conn)
    finally:
        conn.close()
    resultado = executar(separar(df), atraso_dias=atraso_dias)
    rel = resultado["relatorio"]

    ARTEFATOS.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"modelo": resultado["modelo_final"], "limiar": resultado["limiar"], "versao": rel["versao"]},
        ARTEFATOS / "modelo.joblib",
    )
    with open(ARTEFATOS / "metricas.json", "w", encoding="utf-8") as f:
        json.dump(rel, f, indent=2, ensure_ascii=False)
    _resumo(rel)


if __name__ == "__main__":
    main()
