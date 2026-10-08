"""Separacao temporal: cortes sem sobreposicao, sem 2016, pendentes a parte."""
import pandas as pd

from ml.dados import separar


def _amostra():
    linhas = [
        ("a", "2016-12-15", 0),
        ("b", "2017-01-01 00:00:00", 0),
        ("c", "2017-06-10", 1),
        ("d", "2017-12-31 23:59:59", 0),
        ("e", "2018-01-01 00:00:00", 1),
        ("f", "2018-02-20", 0),
        ("g", "2018-05-01 00:00:00", 0),
        ("h", "2018-06-15", 1),
        ("i", "2018-08-31 23:59:59", 0),
        ("j", "2018-06-20", None),
        ("k", "2018-09-01 00:00:00", 0),
    ]
    df = pd.DataFrame(linhas, columns=["pedido_sk", "purchased_at", "atrasou"])
    df["purchased_at"] = pd.to_datetime(df["purchased_at"], format="mixed")
    df["atrasou"] = df["atrasou"].astype("Int64")
    return df


def _no_intervalo(df, ini, fim):
    return df["purchased_at"].between(pd.Timestamp(ini), pd.Timestamp(fim), inclusive="left").all()


def test_separar_cortes_sem_sobreposicao():
    c = separar(_amostra())
    assert _no_intervalo(c["treino"], "2017-01-01", "2018-01-01")
    assert _no_intervalo(c["validacao"], "2018-01-01", "2018-05-01")
    assert _no_intervalo(c["teste"], "2018-05-01", "2018-09-01")
    assert sorted(c["treino"]["pedido_sk"]) == ["b", "c", "d"]
    assert sorted(c["validacao"]["pedido_sk"]) == ["e", "f"]
    assert sorted(c["teste"]["pedido_sk"]) == ["g", "h", "i"]
    chaves = [set(c[k]["pedido_sk"]) for k in ("treino", "validacao", "teste")]
    assert not (chaves[0] & chaves[1]) and not (chaves[0] & chaves[2]) and not (chaves[1] & chaves[2])


def test_separar_exclui_2016():
    c = separar(_amostra())
    for conjunto in c.values():
        assert (conjunto["purchased_at"] >= pd.Timestamp("2017-01-01")).all()
        assert (conjunto["purchased_at"] < pd.Timestamp("2018-09-01")).all()


def test_em_andamento_sao_os_sem_resposta():
    c = separar(_amostra())
    assert list(c["em_andamento"]["pedido_sk"]) == ["j"]
    for k in ("treino", "validacao", "teste"):
        assert "j" not in set(c[k]["pedido_sk"])
        assert c[k]["atrasou"].notna().all()
