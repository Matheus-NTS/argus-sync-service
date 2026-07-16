from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class PeriodWindow:
    period_type: str
    date_from: date
    date_to: date


MVP_PERIODS = [
    "current_month",
    "month_current",
    "month_previous",
    "week_current",
    "week_previous",
    "today",
    "yesterday",
    "last_7_days",
    "last_30_days",
    "ytd",
    "ytd_previous",
]


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _same_day_previous_year(value: date) -> date:
    """
    Retorna a mesma data no ano anterior.

    Protege o caso de 29 de fevereiro:
    29/02 de ano bissexto vira 28/02 do ano anterior,
    caso o ano anterior não seja bissexto.
    """
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(
            year=value.year - 1,
            month=2,
            day=28
        )


def resolve_window(period_type: str, reference_date: date) -> PeriodWindow:

    if period_type in ["current_month", "month_current"]:
        return PeriodWindow(
            period_type=period_type,
            date_from=_month_start(reference_date),
            date_to=reference_date
        )

    if period_type == "month_previous":
        first_current_month = _month_start(reference_date)
        last_previous_month = first_current_month - timedelta(days=1)

        return PeriodWindow(
            period_type=period_type,
            date_from=_month_start(last_previous_month),
            date_to=last_previous_month
        )

    if period_type == "week_current":
        return PeriodWindow(
            period_type=period_type,
            date_from=_week_start(reference_date),
            date_to=reference_date
        )

    if period_type == "week_previous":
        start_current_week = _week_start(reference_date)
        end_previous_week = start_current_week - timedelta(days=1)

        return PeriodWindow(
            period_type=period_type,
            date_from=_week_start(end_previous_week),
            date_to=end_previous_week
        )

    if period_type == "today":
        return PeriodWindow(
            period_type=period_type,
            date_from=reference_date,
            date_to=reference_date
        )

    if period_type == "yesterday":
        yesterday = reference_date - timedelta(days=1)

        return PeriodWindow(
            period_type=period_type,
            date_from=yesterday,
            date_to=yesterday
        )

    if period_type == "last_7_days":
        return PeriodWindow(
            period_type=period_type,
            date_from=reference_date - timedelta(days=6),
            date_to=reference_date
        )

    if period_type == "last_30_days":
        return PeriodWindow(
            period_type=period_type,
            date_from=reference_date - timedelta(days=29),
            date_to=reference_date
        )

    if period_type == "ytd":
        return PeriodWindow(
            period_type=period_type,
            date_from=date(reference_date.year, 1, 1),
            date_to=reference_date
        )

    if period_type == "ytd_previous":
        previous_reference_date = _same_day_previous_year(reference_date)

        return PeriodWindow(
            period_type=period_type,
            date_from=date(previous_reference_date.year, 1, 1),
            date_to=previous_reference_date
        )

    raise ValueError(f"period_type não reconhecido: {period_type}")