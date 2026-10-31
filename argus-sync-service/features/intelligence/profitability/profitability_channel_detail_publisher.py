"""Publicacao isolada do detalhe Atacado x Varejo (ARGUS 3F.3G.1).

Nao altera o dataset de origem nem ativa o fluxo automaticamente.
Requer a migracao 20261029100000_profitability_channel_detail_foundation.sql.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
import uuid

import pandas as pd
import numpy as np

from .profitability_channel_detail import FINANCIAL_COLUMNS

LOAD_TABLE = "mart_profitability_channel_detail_load"
STAGE_TABLE = "mart_profitability_channel_detail_stage"
PUBLISH_RPC = "argus_publish_profitability_channel_detail"
SEGMENTS = frozenset({"Atacado", "Varejo", "Não classificados"})

DETAIL_COLUMNS = (
    "data_venda", "numero_pedido", "empresa_key", "empresa_oficial",
    "vendedor", "codigo_cliente_normalizado", "cliente", "codigo_produto",
    "codigo_fabricante", "produto", "categoria", "curva_abcde", "segmento",
    "elegivel_kpi", *FINANCIAL_COLUMNS,
)
TEXT_REQUIRED = ("empresa_key", "vendedor", "codigo_cliente_normalizado")
TEXT_OPTIONAL = (
    "numero_pedido", "empresa_oficial", "cliente", "codigo_produto",
    "codigo_fabricante", "produto", "categoria", "curva_abcde",
)


def prepare_channel_detail_payload(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    """Valida a carga inteira antes da primeira escrita, sem modificar frame."""
    missing = set(DETAIL_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes no detalhe: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Carga vazia: publicacao bloqueada")

    data = frame.loc[:, list(DETAIL_COLUMNS)].copy()
    dates = pd.to_datetime(data["data_venda"], errors="coerce")
    if dates.isna().any():
        raise ValueError("data_venda invalida")
    data["data_venda"] = dates.dt.date.map(lambda value: value.isoformat())

    for col in TEXT_REQUIRED:
        if not data[col].map(lambda v: isinstance(v, str) and bool(v.strip())).all():
            raise ValueError(f"Dimensao obrigatoria invalida: {col}")
    for col in TEXT_OPTIONAL:
        data[col] = data[col].map(
            lambda value: None if pd.isna(value) else str(value)
        )
    if not data["segmento"].isin(SEGMENTS).all():
        raise ValueError("Segmento invalido")
    if not data["elegivel_kpi"].map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise ValueError("elegivel_kpi deve ser booleano")
    data["elegivel_kpi"] = data["elegivel_kpi"].astype(bool)

    for col in FINANCIAL_COLUMNS:
        def to_decimal(value):
            if pd.isna(value):
                return None
            try:
                result = Decimal(str(value))
            except (ValueError, ArithmeticError) as exc:
                raise ValueError(f"Valor financeiro invalido: {col}") from exc
            if not result.is_finite():
                raise ValueError(f"Valor financeiro nao finito: {col}")
            return result.quantize(
                Decimal("0.000001"),
                rounding=ROUND_HALF_UP,
            )

        data[col] = data[col].map(to_decimal)
    totals = {
        col: math.fsum(
            float(value)
            for value in data[col].tolist()
            if not pd.isna(value)
        )
        for col in FINANCIAL_COLUMNS
    }

    rows = data.to_dict(orient="records")
    for row in rows:
        for col in TEXT_OPTIONAL:
            value = row[col]
            row[col] = None if pd.isna(value) else str(value)

        for col in FINANCIAL_COLUMNS:
            value = row[col]
            row[col] = None if value is None else format(value, "f")
    return rows, {
        "expected_rows": len(rows),
        "expected_revenue": totals["faturamento_analisavel"],
        "expected_cost": totals["custo_analisavel"],
        "expected_profit": totals["lucro_analisavel"],
    }


class ProfitabilityChannelDetailPublisher:
    """Publica staging e solicita substituicao transacional por RPC."""

    def __init__(self, supabase_connector, batch_size: int = 500):
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
            raise ValueError("batch_size deve ser inteiro positivo")
        self.supabase = supabase_connector
        self.batch_size = batch_size

    def publish(self, frame: pd.DataFrame, *, source_as_of: datetime) -> dict:
        if (
            not isinstance(source_as_of, datetime)
            or source_as_of.tzinfo is None
            or source_as_of.utcoffset() is None
        ):
            raise ValueError("source_as_of exige timezone")
        if source_as_of > datetime.now(timezone.utc):
            raise ValueError("source_as_of nao pode estar no futuro")

        rows, expected = prepare_channel_detail_payload(frame)
        run_id = str(uuid.uuid4())
        load = {
            "run_id": run_id,
            "source_as_of": source_as_of.astimezone(timezone.utc).isoformat(),
            **expected,
        }
        try:
            self.supabase.insert(LOAD_TABLE, load)
            self.supabase.insert_batches(
                STAGE_TABLE,
                [{"run_id": run_id, **row} for row in rows],
                batch_size=self.batch_size,
            )
        except Exception as exc:
            raise RuntimeError(
                f"ARGUS_CHANNEL_DETAIL_STAGING_FAILED: run_id={run_id}. "
                "Carga nao publicada; verificar tabelas load/stage antes de nova tentativa."
            ) from exc

        try:
            response = self.supabase.client.rpc(
                PUBLISH_RPC, {"p_run_id": run_id}
            ).execute()
        except Exception as exc:
            raise RuntimeError(
                f"ARGUS_CHANNEL_DETAIL_PUBLICATION_UNCONFIRMED: run_id={run_id}. "
                "Consultar load antes de nova tentativa; nao repetir cegamente."
            ) from exc
        if response.data != expected["expected_rows"]:
            raise RuntimeError(
                f"ARGUS_CHANNEL_DETAIL_PUBLICATION_UNCONFIRMED: run_id={run_id}; "
                f"RPC retornou {response.data!r}, esperado {expected['expected_rows']}."
            )
        return {"run_id": run_id, **expected}
