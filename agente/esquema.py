"""Esquema das marts para o prompt do agente.

Monta um texto curto com cada tabela permitida: grao, colunas com tipo e o
significado vindo dos .yml do dbt, completado por notas onde o nome engana.
O resultado vai para agente/esquema_marts.md, versionado: mudanca no que o
modelo ve aparece no diff.

Uso: python -m agente.esquema   (le o Postgres local e os .yml do dbt)
"""
from __future__ import annotations

from pathlib import Path

import yaml

from agente.config import RAIZ, SCHEMA, TABELAS_PERMITIDAS

GRAOS = {
    "fato_pedidos": "um pedido",
    "fato_itens_pedido": "um item de pedido (um pedido tem um ou mais itens, de vendedores e produtos diferentes)",
    "dim_clientes": "um cliente (pessoa, customer_unique_id)",
    "dim_produtos": "um produto",
    "dim_vendedores": "um vendedor",
    "dim_tempo": "um dia",
    "dim_geolocalizacao": "um prefixo de CEP",
    "previsao_atraso": "um pedido com previsão do modelo de atraso",
}

# O YAML do dbt nao descreve tudo; aqui ficam as colunas em que o nome engana.
NOTAS = {
    "fato_pedidos": {
        "valor_total": "Receita do pedido (itens + frete). É a receita padrão.",
        "valor_itens": "Soma dos preços dos itens, sem frete.",
        "valor_frete": "Soma do frete dos itens.",
        "entregue_no_prazo": "true/false; nulo se o pedido não foi entregue. Taxa de atraso e % no prazo contam só os não nulos.",
        "atraso_dias": "Entrega menos data estimada, em dias: positivo é atraso, negativo é adiantado; nulo se não entregue.",
        "tempo_entrega_dias": "Dias da compra até a entrega ao cliente.",
        "situacao_pedido": "'Entregue', 'Em andamento' ou 'Não concluído'.",
        "nota_avaliacao": "Nota da avaliação do cliente, de 1 a 5; nula sem avaliação.",
        "tempo_sk_compra": "Liga em dim_tempo.tempo_sk (data da compra).",
    },
    "fato_itens_pedido": {
        "valor_item": "Preço do item mais o frete do item. É a receita de itens.",
        "tempo_sk_compra": "Liga em dim_tempo.tempo_sk (data da compra do pedido).",
    },
    "dim_tempo": {
        "ano_mes": "Texto 'AAAA-MM'.",
        "trimestre": "1 a 4.",
    },
    "dim_vendedores": {
        "vendedor_rotulo": "Use para mostrar o vendedor (o seller_id é um hash).",
    },
    "previsao_atraso": {
        "prob_atraso": "Probabilidade de atraso prevista, de 0 a 1.",
        "alerta": "true quando a probabilidade passa o limiar do modelo.",
        "conjunto": "'treino', 'validacao', 'teste' ou 'em_andamento'. Medidas de risco usam só 'teste' e 'em_andamento'.",
    },
}


def ler_descricoes(caminho_yml: Path) -> dict:
    """{tabela: {"descricao": str, "colunas": {coluna: str}}} de models e sources."""
    dados = yaml.safe_load(Path(caminho_yml).read_text(encoding="utf-8")) or {}
    tabelas = list(dados.get("models") or [])
    for fonte in dados.get("sources") or []:
        tabelas.extend(fonte.get("tables") or [])
    saida = {}
    for t in tabelas:
        colunas = {c["name"]: " ".join(str(c.get("description", "")).split())
                   for c in t.get("columns") or [] if c.get("description")}
        saida[t["name"]] = {"descricao": " ".join(str(t.get("description", "")).split()),
                            "colunas": colunas}
    return saida


def montar_esquema(colunas: dict[str, list[tuple[str, str]]], descricoes: dict) -> str:
    """Texto do esquema, so com as tabelas permitidas."""
    partes = [f"## Tabelas disponíveis (schema {SCHEMA})\n"]
    for tabela in TABELAS_PERMITIDAS:
        if tabela not in colunas:
            continue
        info = descricoes.get(tabela, {})
        partes.append(f"### {SCHEMA}.{tabela}")
        if info.get("descricao"):
            partes.append(info["descricao"])
        partes.append(f"Grão: {GRAOS[tabela]}.")
        notas = {**info.get("colunas", {}), **NOTAS.get(tabela, {})}
        for nome, tipo in colunas[tabela]:
            linha = f"- `{nome}` ({tipo})"
            if notas.get(nome):
                linha += f": {notas[nome]}"
            partes.append(linha)
        partes.append("")
    return "\n".join(partes)


def _colunas_do_banco(cur) -> dict[str, list[tuple[str, str]]]:
    cur.execute(
        "select table_name, column_name, data_type from information_schema.columns "
        "where table_schema = %s order by table_name, ordinal_position",
        (SCHEMA,),
    )
    saida: dict[str, list[tuple[str, str]]] = {}
    for tabela, coluna, tipo in cur.fetchall():
        saida.setdefault(tabela, []).append((coluna, tipo))
    return saida


def main() -> None:
    import psycopg2

    from ingestion.config import PG

    descricoes = {}
    for caminho in (RAIZ / "dbt/models/marts/_marts.yml", RAIZ / "dbt/models/ml/_ml.yml"):
        descricoes.update(ler_descricoes(caminho))
    with psycopg2.connect(**PG) as conn, conn.cursor() as cur:
        colunas = _colunas_do_banco(cur)
    destino = Path(__file__).resolve().parent / "esquema_marts.md"
    destino.write_text(montar_esquema(colunas, descricoes), encoding="utf-8")
    print(f"[ok] {destino}")


if __name__ == "__main__":
    main()
