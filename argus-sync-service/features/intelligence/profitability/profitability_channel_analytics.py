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
