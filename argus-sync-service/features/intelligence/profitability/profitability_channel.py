"""Segmentação Atacado x Varejo sobre o dataset oficial de Rentabilidade.

Módulo isolado: não altera o dataset de entrada nem realiza escrita em bancos.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import text

GRAIN = ["data_venda", "empresa_key", "vendedor", "codigo_cliente_normalizado", "segmento"]
FINANCIAL = ["faturamento_analisavel", "custo_analisavel", "lucro_analisavel"]


def read_customer_classifications(sql_connector) -> pd.DataFrame:
    """Consulta somente leitura, usando o engine oficial do Sync Service."""
    query = text("SELECT Codigo_Cliente, Classificacao_1 FROM dbo.agrc_clientes")
    return pd.read_sql(query, sql_connector.engine)


def _code(value):
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def _segment(value):
    if pd.isna(value) or not str(value).strip():
        return "Não classificados"
    return "Atacado" if str(value).strip().upper() == "REVENDA" else "Varejo"


def build_channel_daily(dataset: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Agrega apenas linhas elegíveis, sem deduplicar ocorrências de vendas.

    Histórico: segmento calculado segundo o cadastro recebido nesta execução.
    Contagens distintas de pedidos/clientes não fazem parte deste contrato.
    """
    required_dataset = set(GRAIN[:-1] + FINANCIAL + ["elegivel_kpi"])
    required_customers = {"Codigo_Cliente", "Classificacao_1"}
    missing_dataset = required_dataset - set(dataset.columns)
    missing_customers = required_customers - set(customers.columns)
    if missing_dataset or missing_customers:
        raise KeyError(f"Colunas ausentes: dataset={sorted(missing_dataset)}, cadastro={sorted(missing_customers)}")

    cadastro = customers[["Codigo_Cliente", "Classificacao_1"]].copy()
    cadastro["_codigo"] = cadastro["Codigo_Cliente"].map(_code)
    cadastro = cadastro.loc[cadastro["_codigo"] != ""].copy()
    cadastro["segmento"] = cadastro["Classificacao_1"].map(_segment)
    conflicts = cadastro.groupby("_codigo")["segmento"].nunique()
    if (conflicts > 1).any():
        raise ValueError(f"Classificações conflitantes para clientes: {conflicts[conflicts > 1].index.tolist()[:10]}")
    cadastro = cadastro.drop_duplicates(subset=["_codigo"])[["_codigo", "segmento"]]

    # Sem converter a elegibilidade via astype(bool): strings como 'False' seriam True.
    eligible = dataset["elegivel_kpi"].eq(True)
    base = dataset.loc[eligible, list(required_dataset)].copy()
    base["_codigo"] = base["codigo_cliente_normalizado"].map(_code)
    base["codigo_cliente_normalizado"] = base["_codigo"]
    base["data_venda"] = pd.to_datetime(base["data_venda"], errors="coerce", format="mixed").dt.normalize()
    if base["data_venda"].isna().any():
        raise ValueError("Existem vendas elegíveis com data_venda inválida")
    for col in FINANCIAL:
        base[col] = pd.to_numeric(base[col], errors="raise")
        if base[col].isna().any():
            raise ValueError(f"Valores nulos em {col} para linhas elegíveis")

    base = base.merge(cadastro, on="_codigo", how="left", validate="many_to_one")
    base["segmento"] = base["segmento"].fillna("Não classificados")
    grouped = base.groupby(GRAIN, dropna=False, sort=True)[FINANCIAL].sum().reset_index()

    for col in FINANCIAL:
        before = float(base[col].sum())
        after = float(grouped[col].sum())
        if abs(before - after) > max(0.000001, abs(before) * 1e-12):
            raise AssertionError(f"Falha de conciliação em {col}: {before} != {after}")

    grouped["margem_percentual"] = (
        grouped["lucro_analisavel"].div(grouped["faturamento_analisavel"].where(grouped["faturamento_analisavel"] != 0)) * 100
    )
    grouped["markup_percentual"] = (
        grouped["lucro_analisavel"].div(grouped["custo_analisavel"].where(grouped["custo_analisavel"] != 0)) * 100
    )
    return grouped[GRAIN + FINANCIAL + ["margem_percentual", "markup_percentual"]]
