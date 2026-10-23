"""Indicadores financeiros isolados de Rentabilidade por canal."""

from __future__ import annotations

import math

import pandas as pd

from .profitability_channel_detail import FINANCIAL_COLUMNS


SEGMENTS = ("Atacado", "Varejo", "Não classificados")


def build_channel_overview(detail: pd.DataFrame) -> pd.DataFrame:
    """Consolida os valores elegiveis por canal, sem alterar a entrada."""

    required = {"segmento", "elegivel_kpi", *FINANCIAL_COLUMNS}
    missing = required - set(detail.columns)

    if missing:
        raise KeyError(f"Colunas ausentes: {sorted(missing)}")

    if not detail["segmento"].isin(SEGMENTS).all():
        raise ValueError("Segmento invalido")

    eligible = detail.loc[detail["elegivel_kpi"].eq(True)].copy()

    for column in FINANCIAL_COLUMNS:
        if eligible[column].isna().any():
            raise ValueError(f"Valor financeiro ausente: {column}")

        eligible[column] = pd.to_numeric(
            eligible[column], errors="raise"
        )

        if not eligible[column].map(
            lambda value: math.isfinite(float(value))
        ).all():
            raise ValueError(f"Valor financeiro nao finito: {column}")

    rows = []

    for segment in SEGMENTS:
        group = eligible.loc[eligible["segmento"].eq(segment)]

        revenue = math.fsum(group["faturamento_analisavel"])
        cost = math.fsum(group["custo_analisavel"])
        profit = math.fsum(group["lucro_analisavel"])

        rows.append({
            "segmento": segment,
            "ocorrencias": len(group),
            "faturamento_analisavel": revenue,
            "custo_analisavel": cost,
            "lucro_analisavel": profit,
            "margem_percentual": (
                profit / revenue * 100 if revenue else None
            ),
            "markup_percentual": (
                profit / cost * 100 if cost else None
            ),
        })

    return pd.DataFrame(rows)


GROUPABLE_DIMENSIONS = (
    "empresa_key",
    "vendedor",
    "periodo_mensal",
    "periodo_semanal",
)


def build_channel_grouped(
    detail: pd.DataFrame,
    dimensions: tuple[str, ...],
) -> pd.DataFrame:
    """Agrupa por dimensoes comerciais reutilizando o overview."""

    if not dimensions:
        raise ValueError("Informe ao menos uma dimensao")

    if len(dimensions) != len(set(dimensions)):
        raise ValueError("Dimensoes duplicadas")

    if any(dimension not in GROUPABLE_DIMENSIONS for dimension in dimensions):
        raise ValueError("Dimensao nao permitida")

    missing = set(dimensions) - set(detail.columns)

    if missing:
        raise KeyError(f"Colunas ausentes: {sorted(missing)}")

    frames = []

    for keys, group in detail.groupby(
        list(dimensions),
        dropna=False,
        sort=False,
    ):
        if not isinstance(keys, tuple):
            keys = (keys,)

        overview = build_channel_overview(group)

        for dimension, value in zip(dimensions, keys):
            overview[dimension] = value

        frames.append(overview)

    columns = [
        *dimensions,
        "segmento",
        "ocorrencias",
        *FINANCIAL_COLUMNS,
        "margem_percentual",
        "markup_percentual",
    ]

    if not frames:
        return pd.DataFrame(columns=columns)

    return pd.concat(frames, ignore_index=True)[columns]


def prepare_channel_periods(detail: pd.DataFrame) -> pd.DataFrame:
    """Adiciona mes e inicio da semana sem alterar o detalhe original."""

    if "data_venda" not in detail.columns:
        raise KeyError("Coluna ausente: data_venda")

    new_columns = {"periodo_mensal", "periodo_semanal"}

    if new_columns.intersection(detail.columns):
        raise ValueError("Dimensoes temporais ja existentes")

    result = detail.copy(deep=True)

    dates = pd.to_datetime(result["data_venda"], errors="raise", format="ISO8601")

    if dates.isna().any():
        raise ValueError("Data de venda ausente")

    result["periodo_mensal"] = (
        dates.dt.to_period("M").dt.start_time.dt.date
    )

    result["periodo_semanal"] = (
        dates - pd.to_timedelta(dates.dt.weekday, unit="D")
    ).dt.date

    if len(result) != len(detail):
        raise AssertionError("Quantidade de ocorrencias alterada")

    return result
