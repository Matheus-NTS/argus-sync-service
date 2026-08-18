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
    Calcula os indicadores temporais do módulo Revenue e
    publica a série diária oficial para consumo do frontend.

    A classe recebe a base comercial já filtrada pelo pipeline.
    Ela não reaplica regras comerciais.
    """

    REVENUE_DATE_COLUMN = "Data"
    REVENUE_VALUE_COLUMN = "Valor_total_Unitario"

    VALID_META_STATUSES = {
        "configured",
        "partial",
    }

    COMPANY_COLUMN_CANDIDATES = (
        "empresa",
        "Empresa",
    )

    def __init__(
        self,
        revenue_df: pd.DataFrame,
        meta_df: pd.DataFrame,
        reference_date: date | datetime | pd.Timestamp | str,
        calendar: BusinessCalendar | None = None,
        company_meta_df: pd.DataFrame | None = None,
    ) -> None:
        self.revenue_df = revenue_df
        self.meta_df = meta_df
        self.company_meta_df = company_meta_df
        self.reference_date = self._normalize_date(
            reference_date
        )
        self.calendar = (
            calendar or BusinessCalendar()
        )

        # H3.10: cache local dos atributos de calendário por data.
        # Os atributos dependem apenas da data/calendário, não da empresa.
        # Isso evita recalcular o mesmo month_summary para cada nível
        # (consolidado + empresas) durante build_mart().
        self._calendar_day_cache: dict[date, dict] = {}

    def build(self) -> RevenueDailyResult:
        revenue = self._prepare_revenue()
        meta_mensal = self._resolve_monthly_meta(
            meta_df=self.meta_df,
            year=self.reference_date.year,
            month=self.reference_date.month,
        )

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

    def build_mart(self) -> pd.DataFrame:
        """
        Cria a série diária consolidada e por empresa.

        O calendário útil é obtido pelo BusinessCalendar.
        Para identificar se uma data é útil sem duplicar regra,
        compara-se o contador de dias úteis decorridos do próprio
        calendário entre a data atual e a data anterior.
        """
        revenue = self._prepare_revenue()

        if revenue.empty:
            return pd.DataFrame()

        company_column = self._resolve_company_column(
            revenue
        )

        start_date = (
            revenue[self.REVENUE_DATE_COLUMN]
            .min()
            .date()
        )

        date_dimension = pd.DataFrame({
            "data": pd.date_range(
                start=start_date,
                end=self.reference_date,
                freq="D",
            )
        })

        consolidated = self._build_daily_level(
            revenue=revenue,
            date_dimension=date_dimension,
            meta_df=self.meta_df,
            empresa="Consolidado NTS",
            nivel="consolidado",
        )

        frames = [consolidated]

        if company_column is not None:
            companies = (
                revenue[company_column]
                .dropna()
                .astype(str)
                .str.strip()
            )
            companies = sorted(
                company
                for company in companies.unique()
                if company
            )

            company_meta = (
                self.company_meta_df
                if self.company_meta_df is not None
                else pd.DataFrame()
            )

            for company in companies:
                company_revenue = revenue[
                    revenue[company_column]
                    .astype(str)
                    .str.strip()
                    .eq(company)
                ].copy()

                frames.append(
                    self._build_daily_level(
                        revenue=company_revenue,
                        date_dimension=date_dimension,
                        meta_df=company_meta,
                        empresa=company,
                        nivel="empresa",
                    )
                )

        result = pd.concat(
            frames,
            ignore_index=True,
        )

        result = result.sort_values(
            ["nivel", "empresa", "data"],
            kind="stable",
        ).reset_index(drop=True)

        return result

    def _build_daily_level(
        self,
        revenue: pd.DataFrame,
        date_dimension: pd.DataFrame,
        meta_df: pd.DataFrame,
        empresa: str,
        nivel: str,
    ) -> pd.DataFrame:
        daily_revenue = (
            revenue
            .assign(
                data=revenue[
                    self.REVENUE_DATE_COLUMN
                ].dt.normalize()
            )
            .groupby(
                "data",
                as_index=False,
            )
            .agg(
                faturamento=(
                    self.REVENUE_VALUE_COLUMN,
                    "sum",
                )
            )
        )

        result = date_dimension.merge(
            daily_revenue,
            on="data",
            how="left",
        )

        result["faturamento"] = (
            pd.to_numeric(
                result["faturamento"],
                errors="coerce",
            )
            .fillna(0.0)
            .round(2)
        )

        result["ano"] = result["data"].dt.year
        result["mes"] = result["data"].dt.month
        result["dia"] = result["data"].dt.day
        result["ano_mes"] = (
            result["ano"].astype(str)
            + "-"
            + result["mes"].astype(str).str.zfill(2)
        )
        result["empresa"] = empresa
        result["nivel"] = nivel

        calendar_rows = [
            self._calendar_day_attributes(
                pd.Timestamp(current_date).date()
            )
            for current_date in result["data"]
        ]

        calendar_df = pd.DataFrame(calendar_rows)

        result["dia_util"] = calendar_df[
            "dia_util"
        ].values
        result["dia_util_numero"] = calendar_df[
            "dia_util_numero"
        ].values
        result["dias_uteis_mes"] = calendar_df[
            "dias_uteis_mes"
        ].values

        result["faturamento_acumulado"] = (
            result
            .groupby(
                ["ano", "mes"],
                sort=False,
            )["faturamento"]
            .cumsum()
            .round(2)
        )

        target_records = []

        for (year, month), month_group in result.groupby(
            ["ano", "mes"],
            sort=False,
        ):
            monthly_target = self._resolve_monthly_meta(
                meta_df=meta_df,
                year=int(year),
                month=int(month),
                empresa=(
                    empresa
                    if nivel == "empresa"
                    else None
                ),
            )

            business_days_month = int(
                month_group[
                    "dias_uteis_mes"
                ].max()
            )

            daily_target = self._calculate_daily_target(
                meta_mensal=monthly_target,
                business_days_month=business_days_month,
            )

            for index in month_group.index:
                business_day_number = int(
                    result.at[
                        index,
                        "dia_util_numero",
                    ]
                )

                accumulated_target = (
                    None
                    if daily_target is None
                    else self._round_money(
                        daily_target
                        * business_day_number
                    )
                )

                accumulated_revenue = float(
                    result.at[
                        index,
                        "faturamento_acumulado",
                    ]
                )

                achievement = (
                    None
                    if (
                        accumulated_target is None
                        or accumulated_target <= 0
                    )
                    else round(
                        accumulated_revenue
                        / accumulated_target,
                        6,
                    )
                )

                gap = (
                    None
                    if accumulated_target is None
                    else self._round_money(
                        accumulated_revenue
                        - accumulated_target
                    )
                )

                target_records.append({
                    "index": index,
                    "meta_mensal": monthly_target,
                    "meta_diaria": daily_target,
                    "meta_acumulada": accumulated_target,
                    "atingimento_meta_acumulada": achievement,
                    "gap_acumulado": gap,
                })

        targets = (
            pd.DataFrame(target_records)
            .set_index("index")
        )

        for column in [
            "meta_mensal",
            "meta_diaria",
            "meta_acumulada",
            "atingimento_meta_acumulada",
            "gap_acumulado",
        ]:
            result[column] = targets[column]

        result["data"] = (
            result["data"].dt.date
        )

        return result[[
            "data",
            "ano",
            "mes",
            "dia",
            "ano_mes",
            "empresa",
            "nivel",
            "faturamento",
            "faturamento_acumulado",
            "meta_mensal",
            "meta_diaria",
            "meta_acumulada",
            "atingimento_meta_acumulada",
            "gap_acumulado",
            "dia_util",
            "dia_util_numero",
            "dias_uteis_mes",
        ]].copy()

    def _calendar_day_attributes(
        self,
        current_date: date,
    ) -> dict:
        cached = self._calendar_day_cache.get(
            current_date
        )

        if cached is not None:
            return cached

        current_summary = self.calendar.month_summary(
            current_date
        )

        if current_date.day == 1:
            previous_elapsed = 0
        else:
            previous_date = (
                pd.Timestamp(current_date)
                - pd.Timedelta(days=1)
            ).date()

            if previous_date.month != current_date.month:
                previous_elapsed = 0
            else:
                previous_summary = (
                    self.calendar.month_summary(
                        previous_date
                    )
                )
                previous_elapsed = (
                    previous_summary
                    .dias_uteis_decorridos
                )

        current_elapsed = (
            current_summary.dias_uteis_decorridos
        )

        attributes = {
            "dia_util": (
                current_elapsed > previous_elapsed
            ),
            "dia_util_numero": current_elapsed,
            "dias_uteis_mes": (
                current_summary.dias_uteis_mes
            ),
        }

        self._calendar_day_cache[
            current_date
        ] = attributes

        return attributes

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
        meta_df: pd.DataFrame,
        year: int,
        month: int,
        empresa: str | None = None,
    ) -> float | None:
        if meta_df is None or meta_df.empty:
            return None

        required_columns = {
            "ano",
            "mes",
            "meta",
        }

        missing_columns = (
            required_columns
            - set(meta_df.columns)
        )

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes na base "
                "de metas: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        metas = meta_df.copy()

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
            (metas["ano"] == int(year))
            & (metas["mes"] == int(month))
        ].copy()

        if empresa is not None:
            meta_company_column = (
                self._resolve_company_column(
                    current_meta
                )
            )

            if meta_company_column is None:
                return None

            current_meta = current_meta[
                current_meta[meta_company_column]
                .astype(str)
                .str.strip()
                .eq(str(empresa).strip())
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
    def _resolve_company_column(
        cls,
        dataframe: pd.DataFrame,
    ) -> str | None:
        for column in cls.COMPANY_COLUMN_CANDIDATES:
            if column in dataframe.columns:
                return column

        return None

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