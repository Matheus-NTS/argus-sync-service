"""Enriquecimento isolado do detalhe oficial de Rentabilidade por canal.

Não altera o dataset recebido, não agrega ocorrências e não publica dados.
A classificação atual é uma baseline retrospectiva, não um histórico congelado.
"""

from __future__ import annotations

import math

import pandas as pd

from .profitability_channel import _code, _segment


FINANCIAL_COLUMNS = (
    "faturamento_analisavel",
    "custo_analisavel",
    "lucro_analisavel",
)


def build_channel_detail(
    dataset: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Preserva cada ocorrência do dataset e acrescenta o segmento."""

    if "segmento" in dataset.columns:
        raise ValueError("Dataset já contém segmento")

    required_dataset = {"codigo_cliente_normalizado", *FINANCIAL_COLUMNS}
    required_customers = {"Codigo_Cliente", "Classificacao_1"}

    missing_dataset = required_dataset - set(dataset.columns)
    missing_customers = required_customers - set(customers.columns)

    if missing_dataset or missing_customers:
        raise KeyError(
            f"Colunas ausentes: dataset={sorted(missing_dataset)}, "
            f"cadastro={sorted(missing_customers)}"
        )

    original_columns = list(dataset.columns)
    base = dataset.copy(deep=True)

    cadastro = customers[
        ["Codigo_Cliente", "Classificacao_1"]
    ].copy()

    cadastro["_codigo"] = cadastro["Codigo_Cliente"].map(_code)
    cadastro = cadastro.loc[cadastro["_codigo"] != ""].copy()
    cadastro["segmento"] = cadastro["Classificacao_1"].map(_segment)

    conflicts = cadastro.groupby("_codigo")["segmento"].nunique()

    if (conflicts > 1).any():
        raise ValueError(
            "Classificações conflitantes para clientes: "
            f"{conflicts[conflicts > 1].index.tolist()[:10]}"
        )

    cadastro = cadastro.drop_duplicates(subset=["_codigo"])
    lookup = cadastro.set_index("_codigo")["segmento"]

    codes = base["codigo_cliente_normalizado"].map(_code)

    base["segmento"] = (
        codes.map(lookup).fillna("Não classificados")
    )

    if len(base) != len(dataset):
        raise AssertionError("Quantidade de ocorrências alterada")

    if list(base.columns) != original_columns + ["segmento"]:
        raise AssertionError("Contrato de colunas alterado")

    for column in FINANCIAL_COLUMNS:
        before = pd.to_numeric(dataset[column], errors="raise")
        after = pd.to_numeric(base[column], errors="raise")

        if not before.equals(after):
            raise AssertionError(
                f"Valores financeiros alterados: {column}"
            )

        values = before.dropna().astype(float)

        if not values.map(math.isfinite).all():
            raise ValueError(
                f"Valores financeiros não finitos: {column}"
            )

        if not math.isclose(
            math.fsum(values),
            math.fsum(after.dropna().astype(float)),
            rel_tol=1e-12,
            abs_tol=1e-6,
        ):
            raise AssertionError(
                f"Falha de conciliação: {column}"
            )

    return base
