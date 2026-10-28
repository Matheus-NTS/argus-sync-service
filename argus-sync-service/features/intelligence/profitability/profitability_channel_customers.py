"""Prepara a dimensao atual de clientes por canal."""

from __future__ import annotations

import pandas as pd

from features.intelligence.profitability.profitability_channel import (
    _code,
    _segment,
)

COLUMNS = ("codigo_cliente_normalizado", "segmento")


def prepare_channel_customers(
    customers: pd.DataFrame,
    financial_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
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

    if financial_frame is not None:
        required_financial = {
            "codigo_cliente_normalizado",
            "segmento",
        }
        missing_financial = required_financial - set(financial_frame.columns)

        if missing_financial:
            raise KeyError(
                f"Colunas financeiras ausentes: {sorted(missing_financial)}"
            )

        financial = financial_frame.loc[
            :, ["codigo_cliente_normalizado", "segmento"]
        ].copy()

        if financial["codigo_cliente_normalizado"].isna().any():
            raise ValueError("Financeiro contem codigo de cliente nulo")

        financial_codes = financial["codigo_cliente_normalizado"]

        if not financial_codes.map(
            lambda value: isinstance(value, str) and bool(value.strip())
        ).all():
            raise ValueError("Financeiro contem codigo de cliente invalido")

        if not financial["segmento"].isin(
            {"Atacado", "Varejo", "Não classificados"}
        ).all():
            raise ValueError("Financeiro contem segmento invalido")

        conflicts_financial = (
            financial.groupby("codigo_cliente_normalizado")["segmento"]
            .nunique(dropna=False)
        )

        if conflicts_financial.gt(1).any():
            raise ValueError("Financeiro contem segmentos conflitantes")

        registered = result.set_index("codigo_cliente_normalizado")[
            "segmento"
        ]

        financial_unique = financial.drop_duplicates(
            subset=["codigo_cliente_normalizado"]
        )

        known = financial_unique[
            financial_unique["codigo_cliente_normalizado"].isin(
                registered.index
            )
        ]

        for row in known.itertuples(index=False):
            if registered.loc[row.codigo_cliente_normalizado] != row.segmento:
                raise ValueError(
                    "Divergencia entre cadastro e financeiro: "
                    f"{row.codigo_cliente_normalizado}"
                )

        unknown = financial_unique[
            ~financial_unique["codigo_cliente_normalizado"].isin(
                registered.index
            )
        ]

        if not unknown.empty:
            if not unknown["segmento"].eq(
                "Não classificados"
            ).all():
                raise ValueError(
                    "Cliente sem cadastro possui segmento inesperado"
                )

            result = pd.concat(
                [result, unknown.loc[:, list(COLUMNS)]],
                ignore_index=True,
            )

    return result.loc[:, list(COLUMNS)].reset_index(drop=True)
