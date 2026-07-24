from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

import pandas as pd


DateLike = date | datetime | pd.Timestamp | str


@dataclass(frozen=True)
class BusinessCalendarResult:
    """
    Resumo do calendário comercial para um mês de referência.

    Regras:
    - segunda a sexta-feira são dias potencialmente úteis;
    - sábados e domingos não são úteis;
    - feriados recebidos pelo calendário são excluídos;
    - o dia de referência entra em dias_uteis_decorridos
      quando ele próprio for um dia útil;
    - dias_uteis_restantes não inclui a data de referência.
    """

    reference_date: date
    dias_uteis_mes: int
    dias_uteis_decorridos: int
    dias_uteis_restantes: int
    dia_util_atual: bool
    indice_dia_util: int | None


class BusinessCalendar:
    """
    Calendário comercial compartilhado do ARGUS.

    Esta classe não conhece faturamento, metas, empresas ou Supabase.
    Ela cuida apenas da dimensão temporal.

    Por padrão:
    - segunda a sexta são dias úteis;
    - sábados e domingos não são dias úteis;
    - nenhum feriado é presumido automaticamente.

    Feriados devem ser fornecidos explicitamente para evitar que o ARGUS
    utilize calendários incorretos para Rio de Janeiro, São Paulo, Belém
    ou outras localidades operacionais.

    Exemplo:
        calendar = BusinessCalendar(
            holidays=[
                date(2026, 1, 1),
                date(2026, 4, 21),
            ]
        )
    """

    def __init__(
        self,
        holidays: Iterable[DateLike] | None = None,
    ) -> None:
        self._holidays = frozenset(
            self._normalize_date(value)
            for value in (holidays or [])
        )

    @property
    def holidays(self) -> frozenset[date]:
        return self._holidays

    def is_business_day(
        self,
        value: DateLike,
    ) -> bool:
        """
        Retorna True quando a data for segunda a sexta
        e não estiver cadastrada como feriado.
        """

        normalized_date = self._normalize_date(value)

        is_weekday = normalized_date.weekday() < 5
        is_holiday = normalized_date in self._holidays

        return is_weekday and not is_holiday

    def business_days_month(
        self,
        year: int,
        month: int,
    ) -> int:
        """
        Quantidade total de dias úteis no mês.
        """

        self._validate_year_month(
            year=year,
            month=month,
        )

        start = date(year, month, 1)
        end = self._month_end(
            year=year,
            month=month,
        )

        return self._count_business_days(
            start=start,
            end=end,
        )

    def business_days_elapsed(
        self,
        reference_date: DateLike,
    ) -> int:
        """
        Dias úteis decorridos desde o primeiro dia do mês
        até a data de referência, inclusive.

        Quando a data de referência cair em fim de semana
        ou feriado, conta apenas os dias úteis anteriores.
        """

        normalized_reference = self._normalize_date(
            reference_date
        )

        month_start = normalized_reference.replace(
            day=1
        )

        return self._count_business_days(
            start=month_start,
            end=normalized_reference,
        )

    def business_days_remaining(
        self,
        reference_date: DateLike,
    ) -> int:
        """
        Dias úteis posteriores à data de referência.

        A própria data de referência não é contada como restante,
        mesmo quando for um dia útil.
        """

        normalized_reference = self._normalize_date(
            reference_date
        )

        month_end = self._month_end(
            year=normalized_reference.year,
            month=normalized_reference.month,
        )

        next_date = (
            pd.Timestamp(normalized_reference)
            + pd.Timedelta(days=1)
        ).date()

        if next_date > month_end:
            return 0

        return self._count_business_days(
            start=next_date,
            end=month_end,
        )

    def business_day_index(
        self,
        reference_date: DateLike,
    ) -> int | None:
        """
        Posição do dia útil no mês.

        Exemplos:
        - primeiro dia útil do mês: 1;
        - quinto dia útil do mês: 5;
        - fim de semana ou feriado: None.
        """

        normalized_reference = self._normalize_date(
            reference_date
        )

        if not self.is_business_day(
            normalized_reference
        ):
            return None

        return self.business_days_elapsed(
            normalized_reference
        )

    def month_summary(
        self,
        reference_date: DateLike,
    ) -> BusinessCalendarResult:
        """
        Retorna o resumo completo do calendário comercial
        para o mês da data de referência.
        """

        normalized_reference = self._normalize_date(
            reference_date
        )

        return BusinessCalendarResult(
            reference_date=normalized_reference,
            dias_uteis_mes=self.business_days_month(
                year=normalized_reference.year,
                month=normalized_reference.month,
            ),
            dias_uteis_decorridos=(
                self.business_days_elapsed(
                    normalized_reference
                )
            ),
            dias_uteis_restantes=(
                self.business_days_remaining(
                    normalized_reference
                )
            ),
            dia_util_atual=self.is_business_day(
                normalized_reference
            ),
            indice_dia_util=self.business_day_index(
                normalized_reference
            ),
        )

    def _count_business_days(
        self,
        start: DateLike,
        end: DateLike,
    ) -> int:
        normalized_start = self._normalize_date(
            start
        )
        normalized_end = self._normalize_date(
            end
        )

        if normalized_start > normalized_end:
            return 0

        dates = pd.date_range(
            start=normalized_start,
            end=normalized_end,
            freq="D",
        )

        return sum(
            self.is_business_day(value)
            for value in dates
        )

    @staticmethod
    def _month_end(
        year: int,
        month: int,
    ) -> date:
        BusinessCalendar._validate_year_month(
            year=year,
            month=month,
        )

        return (
            pd.Timestamp(
                year=year,
                month=month,
                day=1,
            )
            + pd.offsets.MonthEnd(1)
        ).date()

    @staticmethod
    def _normalize_date(
        value: DateLike,
    ) -> date:
        if value is None:
            raise ValueError(
                "A data não pode ser None."
            )

        normalized = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(normalized):
            raise ValueError(
                f"Data inválida para o calendário: {value!r}"
            )

        return normalized.date()

    @staticmethod
    def _validate_year_month(
        year: int,
        month: int,
    ) -> None:
        if not isinstance(year, int):
            raise TypeError(
                "O ano deve ser um número inteiro."
            )

        if not isinstance(month, int):
            raise TypeError(
                "O mês deve ser um número inteiro."
            )

        if year < 1:
            raise ValueError(
                "O ano deve ser maior que zero."
            )

        if month < 1 or month > 12:
            raise ValueError(
                "O mês deve estar entre 1 e 12."
            )