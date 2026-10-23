"""Controle do efeito do atraso sobre a nota por categoria, distancia e vendedor.

Reproduz a secao 1.2 de docs/analise-atraso.md (issue #17):

1. A tabela "nota por situacao da entrega" refeita dentro de cada regiao (a
   original, para conferencia), de cada grupo de categoria e de cada faixa de
   distancia vendedor -> cliente.
2. Uma regressao linear da nota (1 a 5) sobre a faixa de atraso, com regiao do
   cliente, grupo de categoria e faixa de distancia como controles, e uma
   versao com efeito fixo de vendedor (compara pedidos do mesmo vendedor).

Erro-padrao agrupado por vendedor: pedidos do mesmo vendedor nao sao
independentes (mesmo despacho, mesmo produto, mesma transportadora), e tratar
cada pedido como independente estreitaria o intervalo de confianca sem motivo.

Uso, da raiz do projeto, depois do dbt build:
    python -m scripts.controle_atraso
"""
from __future__ import annotations

from contextlib import closing

import numpy as np
import pandas as pd

# Mesmas faixas da secao 1 do documento. Pedido entregue sem data de entrega
# (8 casos) fica de fora, como la.
FAIXAS_ATRASO = ["No prazo", "1 a 7 dias", "8 a 30 dias", "Acima de 30 dias"]
FAIXAS_DISTANCIA = ["Até 100 km", "100 a 500 km", "500 a 1.000 km", "1.000 a 2.000 km", "Acima de 2.000 km"]

SQL = """
with itens as (
    select
        i.order_id,
        p.categoria_grupo,
        row_number() over (
            partition by i.order_id order by i.valor_item desc, i.order_item_id
        ) as rn
    from marts.fato_itens_pedido i
    join marts.dim_produtos p on p.produto_sk = i.produto_sk
)
select
    f.pedido_sk,
    f.nota_avaliacao::float8      as nota,
    case
        when f.atraso_dias <= 0  then 'No prazo'
        when f.atraso_dias <= 7  then '1 a 7 dias'
        when f.atraso_dias <= 30 then '8 a 30 dias'
        else 'Acima de 30 dias'
    end                           as faixa_atraso,
    o.cliente_regiao              as regiao,
    it.categoria_grupo            as categoria,
    d.faixa_distancia,
    d.distancia_km::float8        as distancia_km,
    d.distancia_por_cep,
    d.vendedor_sk
from marts.fato_pedidos f
join marts.obt_pedidos o      on o.pedido_sk = f.pedido_sk
join marts.distancia_pedido d on d.pedido_sk = f.pedido_sk
left join itens it            on it.order_id = f.order_id and it.rn = 1
where f.foi_entregue
  and f.atraso_dias is not null
"""


def carregar(conn) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(SQL)
        colunas = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=colunas)


def tabela_por_grupo(df: pd.DataFrame, grupo: str, ordem: list[str] | None = None) -> pd.DataFrame:
    """Nota media por faixa de atraso dentro de cada valor de `grupo`.

    So pedidos avaliados entram na media (o denominador e quem respondeu).
    "Atrasados" conta os avaliados de 1 a 30 dias, para mostrar quando uma
    celula e pequena demais para ler.
    """
    avaliados = df[df["nota"].notna()]
    medias = avaliados.pivot_table(index=grupo, columns="faixa_atraso", values="nota", aggfunc="mean")
    contagem = avaliados.groupby(grupo).size().rename("Pedidos")
    atrasados = (
        avaliados[avaliados["faixa_atraso"].isin(["1 a 7 dias", "8 a 30 dias"])]
        .groupby(grupo).size().rename("Atrasados")
    )
    tab = pd.concat([contagem, atrasados, medias[["No prazo", "1 a 7 dias", "8 a 30 dias"]]], axis=1)
    tab["Queda até 1 a 7"] = tab["No prazo"] - tab["1 a 7 dias"]
    tab["Queda até 8 a 30"] = tab["No prazo"] - tab["8 a 30 dias"]
    if ordem is not None:
        return tab.reindex([g for g in ordem if g in tab.index])
    return tab.sort_values("Pedidos", ascending=False)


def ols_cluster(X: np.ndarray, y: np.ndarray, grupos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Minimos quadrados com erro-padrao robusto agrupado (CR1, o do Stata).

    Devolve coeficientes e erros-padrao. Correcao de amostra pequena
    G/(G-1) * (N-1)/(N-K).
    """
    n, k = X.shape
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ (X.T @ y)
    residuo = y - X @ beta
    _, codigos = np.unique(grupos, return_inverse=True)
    n_grupos = codigos.max() + 1
    escores = np.zeros((n_grupos, k))
    np.add.at(escores, codigos, X * residuo[:, None])
    correcao = n_grupos / (n_grupos - 1) * (n - 1) / (n - k)
    cov = correcao * xtx_inv @ (escores.T @ escores) @ xtx_inv
    return beta, np.sqrt(np.diag(cov))


def centrar_por_grupo(M: np.ndarray, grupos: np.ndarray) -> np.ndarray:
    """Subtrai a media de cada grupo (transformacao within do efeito fixo)."""
    _, codigos = np.unique(grupos, return_inverse=True)
    soma = np.zeros((codigos.max() + 1,) + M.shape[1:])
    np.add.at(soma, codigos, M)
    contagem = np.bincount(codigos).reshape((-1,) + (1,) * (M.ndim - 1))
    return M - (soma / contagem)[codigos]


def matriz(df: pd.DataFrame, controles: list[str]) -> tuple[np.ndarray, list[str]]:
    """Dummies da faixa de atraso (referencia: no prazo) e dos controles.

    Categoria de referencia de cada controle: a de maior volume, para que os
    coeficientes dos controles comparem com o grupo mais comum.
    """
    partes = [pd.get_dummies(pd.Categorical(df["faixa_atraso"], categories=FAIXAS_ATRASO), drop_first=True)]
    for col in controles:
        ordem = df[col].value_counts().index.tolist()
        partes.append(
            pd.get_dummies(pd.Categorical(df[col], categories=ordem), drop_first=True).add_prefix(f"{col}=")
        )
    dummies = pd.concat(partes, axis=1).astype(float)
    X = np.column_stack([np.ones(len(df)), dummies.to_numpy()])
    return X, ["constante"] + list(dummies.columns)


def ajustar(df: pd.DataFrame, controles: list[str], efeito_fixo_vendedor: bool = False) -> pd.DataFrame:
    X, nomes = matriz(df, controles)
    y = df["nota"].to_numpy(dtype=float)
    grupos = df["vendedor_sk"].to_numpy()
    if efeito_fixo_vendedor:
        # Constante some no within; dummies que so variam entre vendedores
        # continuam identificadas porque o vendedor atende varias regioes.
        X, nomes = centrar_por_grupo(X[:, 1:], grupos), nomes[1:]
        y = centrar_por_grupo(y, grupos)
    beta, ep = ols_cluster(X, y, grupos)
    return pd.DataFrame(
        {"coef": beta, "ep": ep, "ic_inf": beta - 1.96 * ep, "ic_sup": beta + 1.96 * ep},
        index=nomes,
    )


ESPECIFICACOES = [
    ("Só atraso", [], False),
    ("+ região", ["regiao"], False),
    ("+ região, categoria e distância", ["regiao", "categoria", "faixa_distancia"], False),
    ("+ efeito fixo de vendedor", ["regiao", "categoria", "faixa_distancia"], True),
]


def _fmt(x: float, casas: int = 2) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def _markdown(tab: pd.DataFrame, titulo: str) -> str:
    linhas = [f"| {titulo} | " + " | ".join(tab.columns) + " |", "|" + "---|" * (len(tab.columns) + 1)]
    for idx, linha in tab.iterrows():
        valores = [
            f"{int(v):,}".replace(",", ".") if c in ("Pedidos", "Atrasados") else _fmt(v)
            for c, v in linha.items()
        ]
        linhas.append(f"| {idx} | " + " | ".join(valores) + " |")
    return "\n".join(linhas)


def main() -> None:
    from ml.config import conectar

    with closing(conectar()) as conn:
        df = carregar(conn)

    print(f"Pedidos entregues com data: {len(df):,}; avaliados: {df['nota'].notna().sum():,}".replace(",", "."))
    for grupo, titulo, ordem in [
        ("regiao", "Região", None),
        ("categoria", "Categoria", None),
        ("faixa_distancia", "Distância", FAIXAS_DISTANCIA),
    ]:
        print()
        print(_markdown(tabela_por_grupo(df, grupo, ordem), titulo))

    amostra = df[df["nota"].notna() & df["distancia_km"].notna()].reset_index(drop=True)
    print(f"\nAmostra da regressao: {len(amostra):,} pedidos avaliados, "
          f"{amostra['vendedor_sk'].nunique():,} vendedores".replace(",", "."))
    print("\n| Especificação | 1 a 7 dias | IC 95% | 8 a 30 dias | IC 95% | Acima de 30 | IC 95% |")
    print("|---|---|---|---|---|---|---|")
    for nome, controles, ef in ESPECIFICACOES:
        r = ajustar(amostra, controles, ef)
        celulas = []
        for faixa in FAIXAS_ATRASO[1:]:
            c = r.loc[faixa]
            celulas += [_fmt(c["coef"]), f"[{_fmt(c['ic_inf'])}; {_fmt(c['ic_sup'])}]"]
        print(f"| {nome} | " + " | ".join(celulas) + " |")

    # Sensibilidade: so pedidos com os dois pontos pelo proprio CEP.
    so_cep = amostra[amostra["distancia_por_cep"]].reset_index(drop=True)
    r = ajustar(so_cep, ["regiao", "categoria", "faixa_distancia"], True)
    c = r.loc["1 a 7 dias"]
    n_cep = f"{len(so_cep):,}".replace(",", ".")
    print(f"\nSo distancia por CEP ({n_cep} pedidos), modelo completo com efeito fixo: "
          f"1 a 7 dias {_fmt(c['coef'])} [{_fmt(c['ic_inf'])}; {_fmt(c['ic_sup'])}]")

    print("\nControles do modelo completo (sem efeito fixo):")
    r = ajustar(amostra, ["regiao", "categoria", "faixa_distancia"], False)
    print(r.round(3).to_string())


if __name__ == "__main__":
    main()
