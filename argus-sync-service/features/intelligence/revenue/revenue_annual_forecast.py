from __future__ import annotations

from datetime import date

import pandas as pd


class RevenueAnnualForecast:
    """
    Forecast operacional de fechamento do ano corrente.

    Regras:
    - utiliza somente meses encerrados do ano corrente;
    - o mes da reference_date permanece em aberto;
    - meses futuros nao participam da base;
    - o forecast anual usa o run-rate medio dos meses fechados;
    - o realizado inclui meses fechados + mes atual em aberto;
    - o ano anterior e usado apenas para comparacao;
    - nao conhece Supabase, frontend ou persistencia.
    """

    REVENUE_COLUMN = "Valor_total_Unitario"
    METHOD = "run_rate_closed_months"

    def __init__(
        self,
        reference_date: date | pd.Timestamp | str | None = None,
    ) -> None:
        self.reference_date = self._normalize_date(
            reference_date or date.today()
        )

    def build(
        self,
        revenue_df: pd.DataFrame,
    ) -> pd.DataFrame:
        revenue = self._prepare_revenue(revenue_df)

        current_year = int(self.reference_date.year)
        current_month = int(self.reference_date.month)
        last_closed_month = current_month - 1

        if last_closed_month < 1:
            raise ValueError(
                "O ano corrente ainda nao possui mes encerrado."
            )

        current_year_data = revenue[
            revenue["ano"].eq(current_year)
        ].copy()

        if current_year_data.empty:
            raise ValueError(
                f"Nao existem vendas para o ano {current_year}."
            )

        closed = current_year_data[
            current_year_data["mes"].between(
                1,
                last_closed_month,
            )
        ].copy()

        closed_months = last_closed_month

        closed_revenue = float(
            closed[self.REVENUE_COLUMN].sum()
        )

        monthly_average = (
            closed_revenue / closed_months
        )

        annual_forecast = (
            monthly_average * 12
        )

        open_month_revenue = float(
            current_year_data.loc[
                current_year_data["mes"].eq(current_month),
                self.REVENUE_COLUMN,
            ].sum()
        )

        realized_revenue = (
            closed_revenue + open_month_revenue
        )

        remaining_estimate = max(
            annual_forecast - realized_revenue,
            0.0,
        )

        previous_year_revenue = float(
            revenue.loc[
                revenue["ano"].eq(current_year - 1),
                self.REVENUE_COLUMN,
            ].sum()
        )

        projected_growth = None

        if previous_year_revenue > 0:
            projected_growth = (
                annual_forecast
                / previous_year_revenue
                - 1
            )

        result = pd.DataFrame([
            {
                "ano": current_year,
                "ultimo_mes_fechado": last_closed_month,
                "meses_fechados": closed_months,
                "faturamento_fechado": closed_revenue,
                "faturamento_mes_aberto": open_month_revenue,
                "faturamento_realizado": realized_revenue,
                "media_mensal_fechada": monthly_average,
                "forecast_anual": annual_forecast,
                "restante_estimado": remaining_estimate,
                "faturamento_ano_anterior": (
                    previous_year_revenue
                ),
                "crescimento_projetado": projected_growth,
                "metodo": self.METHOD,
            }
        ])

        monetary_columns = [
            "faturamento_fechado",
            "faturamento_mes_aberto",
            "faturamento_realizado",
            "media_mensal_fechada",
            "forecast_anual",
            "restante_estimado",
            "faturamento_ano_anterior",
        ]

        result[monetary_columns] = (
            result[monetary_columns].round(2)
        )

        result["crescimento_projetado"] = (
            result["crescimento_projetado"].round(6)
        )

        return result

    @classmethod
    def _prepare_revenue(
        cls,
        revenue_df: pd.DataFrame,
    ) -> pd.DataFrame:
        if revenue_df is None or revenue_df.empty:
            raise ValueError(
                "A base de faturamento esta vazia."
            )

        required_columns = {
            "Data",
            cls.REVENUE_COLUMN,
        }

        missing = (
            required_columns
            - set(revenue_df.columns)
        )

        if missing:
            raise KeyError(
                "Colunas obrigatorias ausentes: "
                + ", ".join(sorted(missing))
            )

        revenue = revenue_df.copy()

        revenue["Data"] = pd.to_datetime(
            revenue["Data"],
            errors="coerce",
        )

        revenue[cls.REVENUE_COLUMN] = pd.to_numeric(
            revenue[cls.REVENUE_COLUMN],
            errors="coerce",
        ).fillna(0.0)

        revenue = revenue[
            revenue["Data"].notna()
        ].copy()

        if revenue.empty:
            raise ValueError(
                "Nenhuma data valida foi encontrada."
            )

        revenue["ano"] = revenue["Data"].dt.year
        revenue["mes"] = revenue["Data"].dt.month

        return revenue

    @staticmethod
    def _normalize_date(
        value: date | pd.Timestamp | str,
    ) -> date:
        normalized = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(normalized):
            raise ValueError(
                f"Data de referencia invalida: {value!r}"
            )

        return normalized.date()
