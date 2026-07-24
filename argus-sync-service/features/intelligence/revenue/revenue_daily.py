from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from features.shared.calendar import BusinessCalendar


@dataclass(frozen=True)
class RevenueDailyResult:
    """
    Indicadores diários consolidados do faturamento.

    Valores monetários podem ser None quando não existe
    uma meta mensal válida para o período.
    """

    reference_date: date
    faturamento_dia: float
    faturamento_mes: float
    meta_mensal: float | None
    meta_diaria: float | None
    ritmo_atual: float
    ritmo_necessario: float | None
    dias_uteis_mes: int
    dias_uteis_decorridos: int
    dias_uteis_restantes: int
    projecao_fechamento: float


class RevenueDaily:
    """
    Calcula os indicadores temporais do módulo Revenue.

    Responsabilidades:
    - faturamento realizado na data de referência;
    - faturamento acumulado do mês;
    - distribuição da meta pelos dias úteis;
    - ritmo médio realizado;
    - ritmo necessário para atingir a meta;
    - projeção de fechamento mantendo o ritmo atual.

    A classe recebe a base oficial já filtrada pelo pipeline.
    Ela não reaplica regras comerciais.
    """

    REVENUE_DATE_COLUMN = "Data"
    REVENUE_VALUE_COLUMN = "Valor_total_Unitario"

    VALID_META_STATUSES = {
        "configured",
        "partial",
    }

    def __init__(
        self,
        revenue_df: pd.DataFrame,
        meta_df: pd.DataFrame,
        reference_date: date | datetime | pd.Timestamp | str,
        calendar: BusinessCalendar | None = None,
    ) -> None:
        self.revenue_df = revenue_df
        self.meta_df = meta_df
        self.reference_date = self._normalize_date(
            reference_date
        )
        self.calendar = (
            calendar or BusinessCalendar()
        )

    def build(self) -> RevenueDailyResult:
        revenue = self._prepare_revenue()
        meta_mensal = self._resolve_monthly_meta()

        calendar_summary = (
            self.calendar.month_summary(
                self.reference_date
            )
        )

        current_month_mask = (
            (revenue[self.REVENUE_DATE_COLUMN].dt.year
             == self.reference_date.year)
            &
            (revenue[self.REVENUE_DATE_COLUMN].dt.month
             == self.reference_date.month)
        )

        current_day_mask = (
            revenue[self.REVENUE_DATE_COLUMN].dt.date
            == self.reference_date
        )

        faturamento_mes = self._round_money(
            revenue.loc[
                current_month_mask,
                self.REVENUE_VALUE_COLUMN,
            ].sum()
        )

        faturamento_dia = self._round_money(
            revenue.loc[
                current_day_mask,
                self.REVENUE_VALUE_COLUMN,
            ].sum()
        )

        meta_diaria = self._calculate_daily_target(
            meta_mensal=meta_mensal,
            business_days_month=(
                calendar_summary.dias_uteis_mes
            ),
        )

        ritmo_atual = self._calculate_current_pace(
            revenue_month=faturamento_mes,
            business_days_elapsed=(
                calendar_summary.dias_uteis_decorridos
            ),
        )

        ritmo_necessario = (
            self._calculate_required_pace(
                revenue_month=faturamento_mes,
                monthly_target=meta_mensal,
                business_days_remaining=(
                    calendar_summary
                    .dias_uteis_restantes
                ),
            )
        )

        projecao_fechamento = self._round_money(
            ritmo_atual
            * calendar_summary.dias_uteis_mes
        )

        return RevenueDailyResult(
            reference_date=self.reference_date,
            faturamento_dia=faturamento_dia,
            faturamento_mes=faturamento_mes,
            meta_mensal=meta_mensal,
            meta_diaria=meta_diaria,
            ritmo_atual=ritmo_atual,
            ritmo_necessario=ritmo_necessario,
            dias_uteis_mes=(
                calendar_summary.dias_uteis_mes
            ),
            dias_uteis_decorridos=(
                calendar_summary
                .dias_uteis_decorridos
            ),
            dias_uteis_restantes=(
                calendar_summary
                .dias_uteis_restantes
            ),
            projecao_fechamento=(
                projecao_fechamento
            ),
        )

    def _prepare_revenue(self) -> pd.DataFrame:
        if self.revenue_df is None:
            raise ValueError(
                "A base de faturamento não pode ser None."
            )

        required_columns = {
            self.REVENUE_DATE_COLUMN,
            self.REVENUE_VALUE_COLUMN,
        }

        missing_columns = (
            required_columns
            - set(self.revenue_df.columns)
        )

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes na base "
                "de faturamento: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        revenue = self.revenue_df.copy()

        revenue[self.REVENUE_DATE_COLUMN] = (
            pd.to_datetime(
                revenue[self.REVENUE_DATE_COLUMN],
                errors="coerce",
            )
        )

        revenue[self.REVENUE_VALUE_COLUMN] = (
            pd.to_numeric(
                revenue[self.REVENUE_VALUE_COLUMN],
                errors="coerce",
            )
            .fillna(0.0)
        )

        revenue = revenue[
            revenue[
                self.REVENUE_DATE_COLUMN
            ].notna()
        ].copy()

        return revenue

    def _resolve_monthly_meta(
        self,
    ) -> float | None:
        if self.meta_df is None:
            return None

        if self.meta_df.empty:
            return None

        required_columns = {
            "ano",
            "mes",
            "meta",
        }

        missing_columns = (
            required_columns
            - set(self.meta_df.columns)
        )

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes na base "
                "de metas: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        metas = self.meta_df.copy()

        metas["ano"] = pd.to_numeric(
            metas["ano"],
            errors="coerce",
        )

        metas["mes"] = pd.to_numeric(
            metas["mes"],
            errors="coerce",
        )

        metas["meta"] = pd.to_numeric(
            metas["meta"],
            errors="coerce",
        )

        current_meta = metas[
            (metas["ano"] == self.reference_date.year)
            & (
                metas["mes"]
                == self.reference_date.month
            )
        ].copy()

        if current_meta.empty:
            return None

        if "status_meta" in current_meta.columns:
            valid_status_mask = (
                current_meta["status_meta"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(self.VALID_META_STATUSES)
            )

            current_meta = current_meta[
                valid_status_mask
            ].copy()

        current_meta = current_meta[
            current_meta["meta"].notna()
            & (current_meta["meta"] > 0)
        ].copy()

        if current_meta.empty:
            return None

        meta_value = current_meta["meta"].sum()

        if pd.isna(meta_value) or meta_value <= 0:
            return None

        return self._round_money(meta_value)

    @classmethod
    def _calculate_daily_target(
        cls,
        meta_mensal: float | None,
        business_days_month: int,
    ) -> float | None:
        if meta_mensal is None:
            return None

        if business_days_month <= 0:
            return None

        return cls._round_money(
            meta_mensal / business_days_month
        )

    @classmethod
    def _calculate_current_pace(
        cls,
        revenue_month: float,
        business_days_elapsed: int,
    ) -> float:
        if business_days_elapsed <= 0:
            return 0.0

        return cls._round_money(
            revenue_month / business_days_elapsed
        )

    @classmethod
    def _calculate_required_pace(
        cls,
        revenue_month: float,
        monthly_target: float | None,
        business_days_remaining: int,
    ) -> float | None:
        if monthly_target is None:
            return None

        remaining_target = max(
            monthly_target - revenue_month,
            0.0,
        )

        if remaining_target == 0:
            return 0.0

        if business_days_remaining <= 0:
            return None

        return cls._round_money(
            remaining_target
            / business_days_remaining
        )

    @staticmethod
    def _normalize_date(
        value: date | datetime | pd.Timestamp | str,
    ) -> date:
        if value is None:
            raise ValueError(
                "A data de referência não pode ser None."
            )

        normalized = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(normalized):
            raise ValueError(
                "Data de referência inválida: "
                f"{value!r}"
            )

        return normalized.date()

    @staticmethod
    def _round_money(
        value,
    ) -> float:
        if pd.isna(value):
            return 0.0

        return round(
            float(value),
            2,
        )