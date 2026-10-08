"""Lista permitida de features e o pre-processamento de cada modelo.

PERMITIDAS e a trava contra vazamento: matriz() so deixa passar essas colunas,
e o teste test_permitidas_e_proibidas_nao_se_cruzam impede que alguem coloque
na lista um campo que so existe depois da compra.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

from ml.config import RANDOM_STATE

NUMERICAS = (
    "prazo_prometido_dias", "distancia_km", "valor_itens", "valor_frete",
    "frete_sobre_valor", "qtd_itens", "qtd_vendedores_distintos",
    "qtd_produtos_distintos", "peso_total_g", "volume_total_cm3", "max_parcelas",
    "dia_semana_compra", "hora_compra",
)
CATEGORICAS = (
    "cliente_uf", "cliente_regiao", "vendedor_uf", "vendedor_regiao",
    "venda_interregional", "categoria_grupo", "tipo_pagamento",
)
PERMITIDAS = NUMERICAS + CATEGORICAS
ALVO = "atrasou"

# Campos que existem no warehouse mas so depois da compra (ou sao o alvo).
# ano_compra e mes_compra existem na compra, mas com um so ano de treino
# identificam eventos de 2017 (Black Friday), nao sazonalidade.
# Motivo de cada um em dbt/models/ml/ml_features_atraso.sql.
PROIBIDAS = (
    "approved_at", "delivered_carrier_at", "dias_ate_transportadora",
    "delivered_customer_at", "tempo_entrega_dias", "dias_em_transporte",
    "atraso_dias", "entregue_no_prazo", "nota_avaliacao", "order_status",
    "status_pedido", "situacao_pedido", "valor_pago", "qtd_pagamentos",
    "ano_compra", "mes_compra",
)


def matriz(df: pd.DataFrame) -> pd.DataFrame:
    """So as colunas permitidas, na ordem de PERMITIDAS, com tipos uniformes."""
    faltando = [c for c in PERMITIDAS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas permitidas ausentes: {', '.join(faltando)}")
    x = df[list(PERMITIDAS)].copy()
    for c in NUMERICAS:
        x[c] = pd.to_numeric(x[c], errors="coerce").astype("float64")
    # Nulo vira np.nan em coluna object: None e NaN misturados confundem os
    # imputadores e codificadores do scikit-learn.
    for c in CATEGORICAS:
        x[c] = x[c].astype(object).where(x[c].notna(), np.nan)
    return x


def modelo_logistica() -> Pipeline:
    """Regressao logistica: mediana nos nulos, padronizacao e one-hot."""
    preparo = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), list(NUMERICAS)),
        ("cat", make_pipeline(
            SimpleImputer(strategy="constant", fill_value="desconhecido"),
            OneHotEncoder(handle_unknown="ignore"),
        ), list(CATEGORICAS)),
    ])
    return Pipeline([
        ("preparo", preparo),
        ("modelo", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])


def modelo_principal(**params) -> Pipeline:
    """Gradient boosting com categoricas nativas e nulos tratados pelo modelo.

    Categoria nunca vista e nulo viram -1, que o HistGradientBoosting trata como
    ausente. Numericas passam como estao (arvores nao precisam de escala).
    """
    preparo = ColumnTransformer(
        [("cat", OrdinalEncoder(
            handle_unknown="use_encoded_value", unknown_value=-1, encoded_missing_value=-1,
        ), list(CATEGORICAS))],
        remainder="passthrough",
    )
    mascara = [True] * len(CATEGORICAS) + [False] * len(NUMERICAS)
    return Pipeline([
        ("preparo", preparo),
        ("modelo", HistGradientBoostingClassifier(
            categorical_features=mascara, max_iter=300, random_state=RANDOM_STATE, **params,
        )),
    ])


def versao_features() -> str:
    """Hash curto da lista permitida: muda sempre que a lista mudar."""
    return hashlib.sha1(",".join(PERMITIDAS).encode()).hexdigest()[:8]
