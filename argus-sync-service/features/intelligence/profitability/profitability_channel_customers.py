"""Prepara a dimensao atual de clientes por canal."""

from __future__ import annotations

import pandas as pd

from features.intelligence.profitability.profitability_channel import (
    _code,
    _segment,
)

COLUMNS = ("codigo_cliente_normalizado", "segmento")


def prepare_channel_customers(customers: pd.DataFrame) -> pd.DataFrame:
    required = {"Codigo_Cliente", "Classificacao_1"}
    missing = required - set(customers.columns)

    if missing:
        raise KeyError(f"Colunas ausentes: {sorted(missing)}")

    result = pd.DataFrame({
        "codigo_cliente_normalizado": customers["Codigo_Cliente"].map(_code),
        "segmento": customers["Classificacao_1"].map(_segment),
    })

    invalid = (
        result["codigo_cliente_normalizado"].isna()
        | result["codigo_cliente_normalizado"].eq("")
    )

    if invalid.any():
        raise ValueError("Cadastro contem codigo de cliente invalido")

    conflicts = (
        result.groupby("codigo_cliente_normalizado")["segmento"]
        .nunique(dropna=False)
    )

    if conflicts.gt(1).any():
        raise ValueError("Classificacoes conflitantes por cliente")

    if result["codigo_cliente_normalizado"].duplicated().any():
        raise ValueError("Cadastro contem codigos duplicados")

    return result.loc[:, list(COLUMNS)].reset_index(drop=True)
