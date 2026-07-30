from features.intelligence.revenue.revenue_daily import (
    RevenueDailyResult,
)
from features.shared.commercial_dimensions import (
    CommercialDimensions,
)
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from features.intelligence.revenue.meta_dataset import (
    MetaDatasetResult,
)


@dataclass(frozen=True)
class RevenueOverviewResult:
    monthly: pd.DataFrame
    company_monthly: pd.DataFrame
    seller_monthly: pd.DataFrame
    current_summary: pd.DataFrame


class RevenueOverview:
    """
    Une faturamento realizado, histórico e metas.

    Entregas:
    - overview mensal consolidado;
    - overview mensal por empresa;
    - overview mensal por empresa e vendedor;
    - resumo do período de referência.

    Regras:
    - meta geral = soma das metas dos vendedores;
    - supermeta = meta + 24%;
    - hipermeta = meta + 37%;
    - meta futura zerada não gera atingimento;
    - meta ausente ou pendente não deve ser interpretada
      como meta válida de R$ 0;
    - vendedor é identificado por Empresa + Vendedor.
    """

    SUPERMETA_FACTOR = 1.24
    HIPERMETA_FACTOR = 1.37

    def __init__(
        self,
        reference_date: date | None = None,
    ):
        self.reference_date = (
            reference_date or date.today()
        )

    def build(
    self,
    history: dict[str, pd.DataFrame],
    metas: MetaDatasetResult,
    daily: RevenueDailyResult,
    ) -> RevenueOverviewResult:
        self._validate_history(history)

        monthly = self._build_monthly(
            history["monthly"],
            metas.general_monthly,
        )

        company_monthly = self._build_company_monthly(
            history["company_monthly"],
            metas.company_monthly,
        )

        seller_monthly = self._build_seller_monthly(
            history["seller_monthly"],
            metas.seller_monthly,
        )

        current_summary = self._build_current_summary(
            monthly=monthly,
            company_monthly=company_monthly,
            seller_monthly=seller_monthly,
            daily=daily,
        )

        return RevenueOverviewResult(
            monthly=monthly,
            company_monthly=company_monthly,
            seller_monthly=seller_monthly,
            current_summary=current_summary,
        )

    def _build_monthly(
        self,
        revenue_monthly: pd.DataFrame,
        meta_monthly: pd.DataFrame,
    ) -> pd.DataFrame:
        revenue = revenue_monthly.copy()
        metas = meta_monthly.copy()

        metas = metas.rename(
            columns={
                "meta": "meta",
                "status_meta": "status_meta",
                "empresas": "empresas_com_meta",
                "vendedores": "vendedores_cadastrados_meta",
            }
        )

        meta_columns = [
            "ano",
            "mes",
            "meta",
            "status_meta",
            "empresas_com_meta",
            "vendedores_cadastrados_meta",
            "vendedores_com_meta",
            "vendedores_pendentes",
        ]

        overview = revenue.merge(
            metas[meta_columns],
            on=[
                "ano",
                "mes",
            ],
            how="left",
        )

        overview["nivel"] = "geral"
        overview["empresa"] = "TOTAL"

        return self._calculate_performance(
            overview
        )

    def _build_company_monthly(
        self,
        revenue_company: pd.DataFrame,
        meta_company: pd.DataFrame,
    ) -> pd.DataFrame:
        revenue = revenue_company.copy()
        metas = meta_company.copy()

        revenue["empresa"] = (
            revenue["Empresa"]
            .apply(
                CommercialDimensions.normalize_company
            )
        )

        revenue = revenue.drop(
            columns=["Empresa"]
        )

        metas = metas.rename(
            columns={
                "vendedores":
                    "vendedores_cadastrados_meta",
            }
        )

        revenue_keys = revenue[
            [
                "ano",
                "mes",
                "ano_mes",
                "empresa",
            ]
        ].drop_duplicates()

        meta_keys = metas[
            [
                "ano",
                "mes",
                "ano_mes",
                "empresa",
            ]
        ].drop_duplicates()

        keys = pd.concat(
            [
                revenue_keys,
                meta_keys,
            ],
            ignore_index=True,
        ).drop_duplicates()

        overview = keys.merge(
            revenue,
            on=[
                "ano",
                "mes",
                "ano_mes",
                "empresa",
            ],
            how="left",
        )

        overview = overview.merge(
            metas[
                [
                    "ano",
                    "mes",
                    "empresa",
                    "meta",
                    "status_meta",
                    "vendedores_cadastrados_meta",
                    "vendedores_com_meta",
                    "vendedores_pendentes",
                ]
            ],
            on=[
                "ano",
                "mes",
                "empresa",
            ],
            how="left",
        )

        revenue_fill_columns = [
            "faturamento",
            "pedidos",
            "vendedores_ativos",
            "ticket_medio",
            "faturamento_total_mes",
            "participacao_mensal",
            "ranking_empresa_mes",
        ]

        for column in revenue_fill_columns:
            if column in overview.columns:
                overview[column] = (
                    overview[column]
                    .fillna(0)
                )

        overview["nivel"] = "empresa"

        return self._calculate_performance(
            overview
        )

    def _build_seller_monthly(
        self,
        revenue_seller: pd.DataFrame,
        meta_seller: pd.DataFrame,
    ) -> pd.DataFrame:
        revenue = revenue_seller.copy()
        metas = meta_seller.copy()

        revenue["empresa"] = (
            revenue["Empresa"]
            .apply(
                CommercialDimensions.normalize_company
            )
        )

        revenue["vendedor_key"] = (
            revenue["Vendedor"]
            .apply(
                CommercialDimensions.normalize_seller
            )
        )

        revenue["vendedor"] = (
            revenue["Vendedor"]
            .apply(
                CommercialDimensions.display_seller_name
            )
        )

        revenue["seller_identity"] = revenue.apply(
            lambda row: (
                CommercialDimensions.seller_identity(
                    company=row["empresa"],
                    seller=row["vendedor_key"],
                )
            ),
            axis=1,
        )

        revenue = revenue.drop(
            columns=[
                "Empresa",
                "Vendedor",
            ]
        )

        revenue_keys = revenue[
            [
                "ano",
                "mes",
                "ano_mes",
                "empresa",
                "vendedor_key",
                "vendedor",
                "seller_identity",
            ]
        ].drop_duplicates()

        meta_keys = metas[
            [
                "ano",
                "mes",
                "ano_mes",
                "empresa",
                "vendedor_key",
                "vendedor",
                "seller_identity",
            ]
        ].drop_duplicates()

        keys = pd.concat(
            [
                revenue_keys,
                meta_keys,
            ],
            ignore_index=True,
        ).drop_duplicates(
            subset=[
                "ano",
                "mes",
                "empresa",
                "vendedor_key",
            ]
        )

        overview = keys.merge(
            revenue,
            on=[
                "ano",
                "mes",
                "ano_mes",
                "empresa",
                "vendedor_key",
                "vendedor",
                "seller_identity",
            ],
            how="left",
        )

        overview = overview.merge(
            metas[
                [
                    "ano",
                    "mes",
                    "empresa",
                    "vendedor_key",
                    "meta",
                    "status_meta",
                    "meta_configurada",
                    "meta_pendente",
                ]
            ],
            on=[
                "ano",
                "mes",
                "empresa",
                "vendedor_key",
            ],
            how="left",
        )

        revenue_fill_columns = [
            "faturamento",
            "pedidos",
            "ticket_medio",
            "faturamento_empresa_mes",
            "participacao_empresa",
            "ranking_vendedor_empresa",
        ]

        for column in revenue_fill_columns:
            if column in overview.columns:
                overview[column] = (
                    overview[column]
                    .fillna(0)
                )

        overview["nivel"] = "vendedor"

        overview = self._calculate_performance(
            overview
        )

        overview = overview.sort_values(
            [
                "ano",
                "mes",
                "empresa",
                "faturamento",
            ],
            ascending=[
                True,
                True,
                True,
                False,
            ],
        ).reset_index(drop=True)

        overview["ranking_faturamento_empresa"] = (
            overview
            .groupby(
                [
                    "ano",
                    "mes",
                    "empresa",
                ]
            )["faturamento"]
            .rank(
                method="dense",
                ascending=False,
            )
            .astype(int)
        )

        configured_mask = (
            overview["meta_valida"]
        )

        overview["ranking_atingimento_empresa"] = np.nan

        overview.loc[
            configured_mask,
            "ranking_atingimento_empresa",
        ] = (
            overview.loc[
                configured_mask
            ]
            .groupby(
                [
                    "ano",
                    "mes",
                    "empresa",
                ]
            )["atingimento_meta"]
            .rank(
                method="dense",
                ascending=False,
            )
        )

        return overview

    def _calculate_performance(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        overview = dataframe.copy()

        if "faturamento" not in overview.columns:
            overview["faturamento"] = 0.0

        overview["faturamento"] = pd.to_numeric(
            overview["faturamento"],
            errors="coerce",
        ).fillna(0.0)

        overview["meta"] = pd.to_numeric(
            overview.get(
                "meta",
                pd.Series(
                    index=overview.index,
                    dtype=float,
                ),
            ),
            errors="coerce",
        )

        overview["status_meta"] = (
            overview.get(
                "status_meta",
                pd.Series(
                    index=overview.index,
                    dtype="object",
                ),
            )
            .fillna("not_registered")
        )

        overview["meta_valida"] = (
            overview["meta"].notna()
            & (overview["meta"] > 0)
            & overview["status_meta"].isin(
                [
                    "configured",
                    "partial",
                ]
            )
        )

        overview["supermeta"] = np.where(
            overview["meta_valida"],
            overview["meta"]
            * self.SUPERMETA_FACTOR,
            np.nan,
        )

        overview["hipermeta"] = np.where(
            overview["meta_valida"],
            overview["meta"]
            * self.HIPERMETA_FACTOR,
            np.nan,
        )

        overview["atingimento_meta"] = np.where(
            overview["meta_valida"],
            overview["faturamento"]
            / overview["meta"],
            np.nan,
        )

        overview["atingimento_supermeta"] = np.where(
            overview["meta_valida"],
            overview["faturamento"]
            / overview["supermeta"],
            np.nan,
        )

        overview["atingimento_hipermeta"] = np.where(
            overview["meta_valida"],
            overview["faturamento"]
            / overview["hipermeta"],
            np.nan,
        )

        overview["gap_meta"] = np.where(
            overview["meta_valida"],
            overview["faturamento"]
            - overview["meta"],
            np.nan,
        )

        overview["gap_supermeta"] = np.where(
            overview["meta_valida"],
            overview["faturamento"]
            - overview["supermeta"],
            np.nan,
        )

        overview["gap_hipermeta"] = np.where(
            overview["meta_valida"],
            overview["faturamento"]
            - overview["hipermeta"],
            np.nan,
        )

        overview["falta_para_meta"] = np.where(
            overview["meta_valida"],
            np.maximum(
                overview["meta"]
                - overview["faturamento"],
                0,
            ),
            np.nan,
        )

        overview["falta_para_supermeta"] = np.where(
            overview["meta_valida"],
            np.maximum(
                overview["supermeta"]
                - overview["faturamento"],
                0,
            ),
            np.nan,
        )

        overview["falta_para_hipermeta"] = np.where(
            overview["meta_valida"],
            np.maximum(
                overview["hipermeta"]
                - overview["faturamento"],
                0,
            ),
            np.nan,
        )

        overview["faixa_desempenho"] = (
            overview.apply(
                self._classify_performance,
                axis=1,
            )
        )

        monetary_columns = [
            "faturamento",
            "meta",
            "supermeta",
            "hipermeta",
            "gap_meta",
            "gap_supermeta",
            "gap_hipermeta",
            "falta_para_meta",
            "falta_para_supermeta",
            "falta_para_hipermeta",
        ]

        for column in monetary_columns:
            if column in overview.columns:
                overview[column] = (
                    overview[column]
                    .round(2)
                )

        percentage_columns = [
            "atingimento_meta",
            "atingimento_supermeta",
            "atingimento_hipermeta",
        ]

        for column in percentage_columns:
            overview[column] = (
                overview[column]
                .round(6)
            )

        return overview

    @staticmethod
    def _classify_performance(
        row: pd.Series,
    ) -> str:
        status_meta = row.get(
            "status_meta",
            "not_registered",
        )

        if status_meta == "pending":
            return "meta_pendente"

        if status_meta == "missing":
            return "sem_meta"

        if status_meta == "not_registered":
            return "meta_nao_cadastrada"

        if not bool(
            row.get("meta_valida", False)
        ):
            return "sem_meta_valida"

        revenue = float(
            row.get("faturamento", 0)
        )

        target = float(
            row.get("meta", 0)
        )

        super_target = float(
            row.get("supermeta", 0)
        )

        hyper_target = float(
            row.get("hipermeta", 0)
        )

        if revenue >= hyper_target:
            return "hipermeta"

        if revenue >= super_target:
            return "supermeta"

        if revenue >= target:
            return "meta"

        return "abaixo_meta"

    def _build_current_summary(
    self,
    monthly: pd.DataFrame,
    company_monthly: pd.DataFrame,
    seller_monthly: pd.DataFrame,
    daily: RevenueDailyResult,
    ) -> pd.DataFrame:
        year = self.reference_date.year
        month = self.reference_date.month

        current = monthly[
            (monthly["ano"] == year)
            & (monthly["mes"] == month)
        ].copy()

        if current.empty:
            return pd.DataFrame(
                [
                    {
                        "reference_date": pd.Timestamp(
                            self.reference_date
                        ),
                        "ano": year,
                        "mes": month,
                        "status": "period_not_available",
                    }
                ]
            )

        current_row = current.iloc[0]

        current_companies = company_monthly[
            (company_monthly["ano"] == year)
            & (company_monthly["mes"] == month)
        ].copy()

        current_sellers = seller_monthly[
            (seller_monthly["ano"] == year)
            & (seller_monthly["mes"] == month)
        ].copy()

        sellers_with_valid_target = current_sellers[
            current_sellers["meta_valida"]
        ]

        faturamento_dia = float(
            daily.faturamento_dia or 0
        )

        meta_diaria = float(
            daily.meta_diaria or 0
        )

        meta_diaria_valida = (
            meta_diaria > 0
        )

        supermeta_diaria = (
            meta_diaria * self.SUPERMETA_FACTOR
            if meta_diaria_valida
            else 0.0
        )

        hipermeta_diaria = (
            meta_diaria * self.HIPERMETA_FACTOR
            if meta_diaria_valida
            else 0.0
        )

        atingimento_meta_diaria = (
            faturamento_dia / meta_diaria
            if meta_diaria_valida
            else 0.0
        )

        gap_meta_diaria = (
            faturamento_dia - meta_diaria
            if meta_diaria_valida
            else 0.0
        )

        gap_supermeta_diaria = (
            faturamento_dia - supermeta_diaria
            if meta_diaria_valida
            else 0.0
        )

        gap_hipermeta_diaria = (
            faturamento_dia - hipermeta_diaria
            if meta_diaria_valida
            else 0.0
        )

        falta_para_meta_diaria = (
            max(meta_diaria - faturamento_dia, 0.0)
            if meta_diaria_valida
            else 0.0
        )

        falta_para_supermeta_diaria = (
            max(supermeta_diaria - faturamento_dia, 0.0)
            if meta_diaria_valida
            else 0.0
        )

        falta_para_hipermeta_diaria = (
            max(hipermeta_diaria - faturamento_dia, 0.0)
            if meta_diaria_valida
            else 0.0
        )

        if not meta_diaria_valida:
            faixa_desempenho_diaria = (
                "sem_meta_diaria"
            )
            status_meta_diaria = (
                "not_available"
            )
        elif faturamento_dia >= hipermeta_diaria:
            faixa_desempenho_diaria = (
                "hipermeta"
            )
            status_meta_diaria = (
                "achieved"
            )
        elif faturamento_dia >= supermeta_diaria:
            faixa_desempenho_diaria = (
                "supermeta"
            )
            status_meta_diaria = (
                "achieved"
            )
        elif faturamento_dia >= meta_diaria:
            faixa_desempenho_diaria = (
                "meta"
            )
            status_meta_diaria = (
                "achieved"
            )
        else:
            faixa_desempenho_diaria = (
                "abaixo_meta"
            )
            status_meta_diaria = (
                "below_target"
            )
        
        record = {
            "reference_date": pd.Timestamp(
                self.reference_date
            ),
            "ano": year,
            "mes": month,
            "faturamento": float(
                current_row["faturamento"]
            ),
                        "faturamento_dia": round(
                faturamento_dia,
                2,
            ),
            "meta_diaria": round(
                meta_diaria,
                2,
            ),
            "supermeta_diaria": round(
                supermeta_diaria,
                2,
            ),
            "hipermeta_diaria": round(
                hipermeta_diaria,
                2,
            ),
            "atingimento_meta_diaria": round(
                atingimento_meta_diaria,
                6,
            ),
            "gap_meta_diaria": round(
                gap_meta_diaria,
                2,
            ),
            "gap_supermeta_diaria": round(
                gap_supermeta_diaria,
                2,
            ),
            "gap_hipermeta_diaria": round(
                gap_hipermeta_diaria,
                2,
            ),
            "falta_para_meta_diaria": round(
                falta_para_meta_diaria,
                2,
            ),
            "falta_para_supermeta_diaria": round(
                falta_para_supermeta_diaria,
                2,
            ),
            "falta_para_hipermeta_diaria": round(
                falta_para_hipermeta_diaria,
                2,
            ),
            "status_meta_diaria": (
                status_meta_diaria
            ),
            "faixa_desempenho_diaria": (
                faixa_desempenho_diaria
            ),
            "ritmo_atual": daily.ritmo_atual,
            "ritmo_necessario": daily.ritmo_necessario,
            "dias_uteis_mes": daily.dias_uteis_mes,
            "dias_uteis_decorridos": (
                daily.dias_uteis_decorridos
            ),
            "dias_uteis_restantes": (
                daily.dias_uteis_restantes
            ),
            "projecao_fechamento": (
                daily.projecao_fechamento
            ),
            "meta": self._safe_float(
                current_row.get("meta")
            ),
            "supermeta": self._safe_float(
                current_row.get("supermeta")
            ),
            "hipermeta": self._safe_float(
                current_row.get("hipermeta")
            ),
            "atingimento_meta": self._safe_float(
                current_row.get(
                    "atingimento_meta"
                )
            ),
            "gap_meta": self._safe_float(
                current_row.get("gap_meta")
            ),
            "status_meta": current_row.get(
                "status_meta"
            ),
            "faixa_desempenho": current_row.get(
                "faixa_desempenho"
            ),
            "empresas_com_faturamento": int(
                (
                    current_companies["faturamento"]
                    > 0
                ).sum()
            ),
            "vendedores_com_faturamento": int(
                (
                    current_sellers["faturamento"]
                    > 0
                ).sum()
            ),
            "vendedores_com_meta_valida": int(
                sellers_with_valid_target.shape[0]
            ),
            "vendedores_que_bateram_meta": int(
                (
                    sellers_with_valid_target[
                        "atingimento_meta"
                    ] >= 1
                ).sum()
            ),
            "vendedores_em_supermeta": int(
                (
                    sellers_with_valid_target[
                        "atingimento_meta"
                    ] >= self.SUPERMETA_FACTOR
                ).sum()
            ),
            "vendedores_em_hipermeta": int(
                (
                    sellers_with_valid_target[
                        "atingimento_meta"
                    ] >= self.HIPERMETA_FACTOR
                ).sum()
            ),
            "status": "available",
        }

        return pd.DataFrame([record])

    @staticmethod
    def _safe_float(
        value,
    ) -> float | None:
        if pd.isna(value):
            return None

        return round(
            float(value),
            6,
        )

    @staticmethod
    def _validate_history(
        history: dict[str, pd.DataFrame],
    ) -> None:
        required = {
            "monthly",
            "company_monthly",
            "seller_monthly",
        }

        missing = (
            required
            - set(history.keys())
        )

        if missing:
            raise KeyError(
                "Visões históricas obrigatórias ausentes: "
                + ", ".join(
                    sorted(missing)
                )
            )