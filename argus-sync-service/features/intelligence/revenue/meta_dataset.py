from features.shared.commercial_dimensions import (
    CommercialDimensions,
)
from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class MetaDatasetResult:
    seller_monthly: pd.DataFrame
    company_monthly: pd.DataFrame
    general_monthly: pd.DataFrame


class MetaDataset:
    """
    Prepara a base oficial de metas do ARGUS.

    Granularidade principal:
        empresa + vendedor + ano + mes

    Regras:
    - Meta da empresa = soma das metas dos vendedores.
    - Meta geral = soma das metas de todas as empresas.
    - Meta futura zerada = pendente de preenchimento.
    - Meta passada ou atual zerada = sem meta cadastrada.
    - A identidade do vendedor é Empresa + Vendedor.
    """

    REQUIRED_COLUMNS = {
        "mes",
        "ano",
        "vendedor",
        "valor",
        "Empresa",
    }

    def __init__(
        self,
        reference_date: date | None = None,
    ):
        self.reference_date = (
            reference_date or date.today()
        )

    def _validate_columns(
        self,
        metas_df: pd.DataFrame,
    ) -> None:
        missing = (
            self.REQUIRED_COLUMNS
            - set(metas_df.columns)
        )

        if missing:
            raise KeyError(
                "Colunas obrigatórias ausentes na base "
                f"de metas: {sorted(missing)}"
            )

    def _period_status(
        self,
        year: int,
        month: int,
        value: float,
    ) -> str:

        reference_period = (
            self.reference_date.year,
            self.reference_date.month,
        )

        row_period = (
            year,
            month,
        )

        if value > 0:
            return "configured"

        if row_period > reference_period:
            return "pending"

        return "missing"

    def build(
        self,
        metas_df: pd.DataFrame,
    ) -> MetaDatasetResult:
        self._validate_columns(metas_df)

        metas = metas_df.copy()

        metas["ano"] = pd.to_numeric(
            metas["ano"],
            errors="coerce",
        )

        metas["mes"] = pd.to_numeric(
            metas["mes"],
            errors="coerce",
        )

        metas["meta"] = pd.to_numeric(
            metas["valor"],
            errors="coerce",
        )

        metas["empresa"] = metas[
            "Empresa"
        ].apply(
            CommercialDimensions.normalize_company
        )

        metas["vendedor_key"] = metas[
            "vendedor"
        ].apply(
            CommercialDimensions.normalize_seller
        )

        metas["vendedor"] = metas[
            "vendedor"
        ].apply(
            CommercialDimensions.display_seller_name
        )

        invalid_mask = (
            metas["ano"].isna()
            | metas["mes"].isna()
            | metas["meta"].isna()
            | metas["empresa"].eq("")
            | metas["vendedor_key"].eq("")
        )

        if invalid_mask.any():
            invalid_count = int(
                invalid_mask.sum()
            )

            raise ValueError(
                "A base de metas possui "
                f"{invalid_count:,} linha(s) inválida(s)."
            )

        metas["ano"] = metas[
            "ano"
        ].astype(int)

        metas["mes"] = metas[
            "mes"
        ].astype(int)

        invalid_month = ~metas[
            "mes"
        ].between(1, 12)

        if invalid_month.any():
            raise ValueError(
                "Foram encontrados meses fora "
                "do intervalo de 1 a 12."
            )

        key_columns = [
            "empresa",
            "vendedor_key",
            "ano",
            "mes",
        ]

        duplicate_mask = metas.duplicated(
            subset=key_columns,
            keep=False,
        )

        if duplicate_mask.any():
            duplicates = metas.loc[
                duplicate_mask,
                key_columns + ["meta"],
            ]

            raise ValueError(
                "Existem metas duplicadas na chave "
                "Empresa + Vendedor + Ano + Mês:\n"
                + duplicates.to_string(
                    index=False
                )
            )

        metas["reference_date"] = pd.Timestamp(
            self.reference_date
        )

        metas["period_start"] = pd.to_datetime(
            {
                "year": metas["ano"],
                "month": metas["mes"],
                "day": 1,
            }
        )

        metas["ano_mes"] = (
            metas["ano"].astype(str)
            + "-"
            + metas["mes"]
            .astype(str)
            .str.zfill(2)
        )

        metas["status_meta"] = metas.apply(
            lambda row: self._period_status(
                year=int(row["ano"]),
                month=int(row["mes"]),
                value=float(row["meta"]),
            ),
            axis=1,
        )

        metas["meta_configurada"] = (
            metas["status_meta"]
            == "configured"
        )

        metas["meta_pendente"] = (
            metas["status_meta"]
            == "pending"
        )

        metas["seller_identity"] = metas.apply(
            lambda row: (
                CommercialDimensions.seller_identity(
                    company=row["empresa"],
                    seller=row["vendedor_key"],
                )
            ),
            axis=1,
        )

        seller_monthly = metas[
            [
                "reference_date",
                "period_start",
                "ano",
                "mes",
                "ano_mes",
                "empresa",
                "vendedor_key",
                "vendedor",
                "seller_identity",
                "meta",
                "status_meta",
                "meta_configurada",
                "meta_pendente",
            ]
        ].sort_values(
            [
                "ano",
                "mes",
                "empresa",
                "vendedor_key",
            ]
        ).reset_index(
            drop=True
        )

        company_monthly = (
            seller_monthly
            .groupby(
                [
                    "reference_date",
                    "period_start",
                    "ano",
                    "mes",
                    "ano_mes",
                    "empresa",
                ],
                as_index=False,
            )
            .agg(
                meta=(
                    "meta",
                    "sum",
                ),
                vendedores=(
                    "seller_identity",
                    "nunique",
                ),
                vendedores_com_meta=(
                    "meta_configurada",
                    "sum",
                ),
                vendedores_pendentes=(
                    "meta_pendente",
                    "sum",
                ),
            )
        )

        company_monthly["status_meta"] = (
            company_monthly.apply(
                self._aggregate_status,
                axis=1,
            )
        )

        general_monthly = (
            company_monthly
            .groupby(
                [
                    "reference_date",
                    "period_start",
                    "ano",
                    "mes",
                    "ano_mes",
                ],
                as_index=False,
            )
            .agg(
                meta=(
                    "meta",
                    "sum",
                ),
                empresas=(
                    "empresa",
                    "nunique",
                ),
                vendedores=(
                    "vendedores",
                    "sum",
                ),
                vendedores_com_meta=(
                    "vendedores_com_meta",
                    "sum",
                ),
                vendedores_pendentes=(
                    "vendedores_pendentes",
                    "sum",
                ),
            )
        )

        general_monthly["empresa"] = "TOTAL"

        general_monthly["status_meta"] = (
            general_monthly.apply(
                self._aggregate_status,
                axis=1,
            )
        )

        return MetaDatasetResult(
            seller_monthly=seller_monthly,
            company_monthly=company_monthly,
            general_monthly=general_monthly,
        )

    @staticmethod
    def _aggregate_status(
        row: pd.Series,
    ) -> str:
        total = int(
            row.get("vendedores", 0)
        )

        configured = int(
            row.get(
                "vendedores_com_meta",
                0,
            )
        )

        pending = int(
            row.get(
                "vendedores_pendentes",
                0,
            )
        )

        if total > 0 and configured == total:
            return "configured"

        if total > 0 and pending == total:
            return "pending"

        if configured > 0:
            return "partial"

        if pending > 0:
            return "pending"

        return "missing"