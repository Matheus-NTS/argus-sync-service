from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from features.shared.calendar import BusinessCalendar


class SellerPace:
    """
    Calcula ritmo e projeção mensal por vendedor.

    A matemática segue a mesma metodologia de RevenueDaily:
    - meta diária = meta mensal / dias úteis do mês;
    - ritmo atual = faturamento / dias úteis decorridos;
    - ritmo necessário = valor restante / dias úteis restantes;
    - projeção = ritmo atual * dias úteis do mês.

    O cálculo é aplicável somente ao mês atual. Para outros
    períodos, os campos temporais ficam sem valor e o status
    recebe "nao_aplicavel".
    """

    APPLICABLE_PERIODS = {
        "current_month",
        "month_current",
    }

    def __init__(
        self,
        reference_date: date | datetime | pd.Timestamp | str,
        calendar: BusinessCalendar | None = None,
    ) -> None:
        self.reference_date = self._normalize_date(
            reference_date
        )
        self.calendar = (
            calendar or BusinessCalendar()
        )

    def build(
        self,
        seller_df: pd.DataFrame,
        period_type: str,
    ) -> pd.DataFrame:

        if seller_df is None:
            raise ValueError(
                "seller_df não pode ser None."
            )

        result = seller_df.copy()

        self._initialize_columns(result)

        if (
            result.empty
            or period_type not in self.APPLICABLE_PERIODS
        ):
            return result

        calendar_summary = (
            self.calendar.month_summary(
                self.reference_date
            )
        )

        dias_uteis_mes = int(
            calendar_summary.dias_uteis_mes
        )

        dias_uteis_decorridos = int(
            calendar_summary.dias_uteis_decorridos
        )

        dias_uteis_restantes = int(
            calendar_summary.dias_uteis_restantes
        )

        result["pace_applicable"] = True
        result["dias_uteis_mes"] = dias_uteis_mes
        result["dias_uteis_decorridos"] = (
            dias_uteis_decorridos
        )
        result["dias_uteis_restantes"] = (
            dias_uteis_restantes
        )

        result["meta_diaria"] = result.apply(
            lambda row: self._calculate_daily_target(
                monthly_target=row.get(
                    "meta_mensal"
                ),
                valid_target=bool(
                    row.get("meta_valida", False)
                ),
                business_days_month=dias_uteis_mes,
            ),
            axis=1,
        )

        result["ritmo_atual"] = result.apply(
            lambda row: self._calculate_current_pace(
                revenue_month=row.get(
                    "faturamento_total", 0
                ),
                business_days_elapsed=(
                    dias_uteis_decorridos
                ),
            ),
            axis=1,
        )

        result["ritmo_necessario"] = result.apply(
            lambda row: self._calculate_required_pace(
                revenue_month=row.get(
                    "faturamento_total", 0
                ),
                monthly_target=row.get(
                    "meta_mensal"
                ),
                valid_target=bool(
                    row.get("meta_valida", False)
                ),
                business_days_remaining=(
                    dias_uteis_restantes
                ),
            ),
            axis=1,
        )

        result["projecao_fechamento"] = (
            result["ritmo_atual"]
            * dias_uteis_mes
        ).round(2)

        result["projecao_atingimento"] = (
            result.apply(
                self._calculate_projection_attainment,
                axis=1,
            )
        )

        result["projecao_atinge_meta"] = (
            result.apply(
                lambda row: (
                    bool(row.get("meta_valida", False))
                    and float(
                        row.get(
                            "projecao_fechamento",
                            0,
                        )
                        or 0
                    )
                    >= float(
                        row.get("meta_mensal", 0)
                        or 0
                    )
                ),
                axis=1,
            )
        )

        result["status_projecao"] = (
            result.apply(
                self._classify_projection,
                axis=1,
            )
        )

        return result

    @staticmethod
    def _initialize_columns(
        dataframe: pd.DataFrame,
    ) -> None:

        dataframe["pace_applicable"] = False
        dataframe["dias_uteis_mes"] = pd.NA
        dataframe["dias_uteis_decorridos"] = pd.NA
        dataframe["dias_uteis_restantes"] = pd.NA
        dataframe["meta_diaria"] = pd.NA
        dataframe["ritmo_atual"] = pd.NA
        dataframe["ritmo_necessario"] = pd.NA
        dataframe["projecao_fechamento"] = pd.NA
        dataframe["projecao_atingimento"] = pd.NA
        dataframe["projecao_atinge_meta"] = False
        dataframe["status_projecao"] = (
            "nao_aplicavel"
        )

    @classmethod
    def _calculate_daily_target(
        cls,
        monthly_target,
        valid_target: bool,
        business_days_month: int,
    ) -> float | None:

        if not valid_target:
            return None

        if business_days_month <= 0:
            return None

        return cls._round_money(
            float(monthly_target)
            / business_days_month
        )

    @classmethod
    def _calculate_current_pace(
        cls,
        revenue_month,
        business_days_elapsed: int,
    ) -> float:

        if business_days_elapsed <= 0:
            return 0.0

        return cls._round_money(
            float(revenue_month or 0)
            / business_days_elapsed
        )

    @classmethod
    def _calculate_required_pace(
        cls,
        revenue_month,
        monthly_target,
        valid_target: bool,
        business_days_remaining: int,
    ) -> float | None:

        if not valid_target:
            return None

        remaining_target = max(
            float(monthly_target or 0)
            - float(revenue_month or 0),
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
    def _calculate_projection_attainment(
        row: pd.Series,
    ) -> float | None:

        if not bool(
            row.get("meta_valida", False)
        ):
            return None

        monthly_target = float(
            row.get("meta_mensal", 0)
            or 0
        )

        if monthly_target <= 0:
            return None

        projection = float(
            row.get("projecao_fechamento", 0)
            or 0
        )

        return round(
            projection / monthly_target,
            6,
        )

    @staticmethod
    def _classify_projection(
        row: pd.Series,
    ) -> str:

        if not bool(
            row.get("pace_applicable", False)
        ):
            return "nao_aplicavel"

        if not bool(
            row.get("meta_valida", False)
        ):
            return "sem_meta"

        if bool(
            row.get(
                "projecao_atinge_meta",
                False,
            )
        ):
            return "atinge_meta"

        return "nao_atinge_meta"

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