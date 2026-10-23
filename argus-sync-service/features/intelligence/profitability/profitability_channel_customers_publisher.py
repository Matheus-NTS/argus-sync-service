"""Publicacao isolada da dimensao atual de clientes por canal."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pandas as pd

from .profitability_channel_customers import COLUMNS

LOAD_TABLE = "mart_profitability_channel_customers_load"
STAGE_TABLE = "mart_profitability_channel_customers_stage"
PUBLISH_RPC = "argus_publish_profitability_channel_customers"

SEGMENTS = frozenset({
    "Atacado",
    "Varejo",
    "N\u00e3o classificados",
})


def prepare_customers_payload(frame: pd.DataFrame) -> list[dict]:
    """Valida a dimensao antes de qualquer operacao de escrita."""
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")

    if frame.empty:
        raise ValueError("Carga vazia: publicacao bloqueada")

    data = frame.loc[:, list(COLUMNS)].copy()

    codes = data["codigo_cliente_normalizado"]
    if not codes.map(
        lambda value: isinstance(value, str) and bool(value.strip())
    ).all():
        raise ValueError("Codigo de cliente invalido")

    if codes.duplicated().any():
        raise ValueError("Codigos de cliente duplicados")

    if not data["segmento"].isin(SEGMENTS).all():
        raise ValueError("Segmento invalido")

    return data.to_dict(orient="records")


class ProfitabilityChannelCustomersPublisher:
    """Envia staging e solicita publicacao transacional por RPC."""

    def __init__(self, supabase_connector, batch_size: int = 500):
        if (
            not isinstance(batch_size, int)
            or isinstance(batch_size, bool)
            or batch_size <= 0
        ):
            raise ValueError("batch_size deve ser inteiro positivo")

        self.supabase = supabase_connector
        self.batch_size = batch_size

    def publish(
        self,
        frame: pd.DataFrame,
        *,
        source_as_of: datetime,
    ) -> dict:
        if (
            not isinstance(source_as_of, datetime)
            or source_as_of.tzinfo is None
            or source_as_of.utcoffset() is None
        ):
            raise ValueError("source_as_of exige timezone")

        if source_as_of > datetime.now(timezone.utc):
            raise ValueError("source_as_of nao pode estar no futuro")

        rows = prepare_customers_payload(frame)
        run_id = str(uuid.uuid4())

        load = {
            "run_id": run_id,
            "source_as_of": source_as_of.astimezone(
                timezone.utc
            ).isoformat(),
            "expected_rows": len(rows),
        }

        try:
            self.supabase.insert(LOAD_TABLE, load)
            stage = [
                {"run_id": run_id, **row}
                for row in rows
            ]
            self.supabase.insert_batches(
                STAGE_TABLE,
                stage,
                batch_size=self.batch_size,
            )
        except Exception as exc:
            raise RuntimeError(
                "ARGUS_CHANNEL_CUSTOMERS_STAGING_FAILED: "
                f"run_id={run_id}. "
                "Carga nao publicada; verificar staging e load."
            ) from exc

        try:
            response = self.supabase.client.rpc(
                PUBLISH_RPC,
                {"p_run_id": run_id},
            ).execute()
        except Exception as exc:
            raise RuntimeError(
                "ARGUS_CHANNEL_CUSTOMERS_PUBLICATION_UNCONFIRMED: "
                f"run_id={run_id}. "
                "Consultar load antes de nova tentativa."
            ) from exc

        if response.data != len(rows):
            raise RuntimeError(
                "ARGUS_CHANNEL_CUSTOMERS_PUBLICATION_UNCONFIRMED: "
                f"run_id={run_id}. "
                f"Retorno inesperado: {response.data!r}."
            )

        return {
            "run_id": run_id,
            "expected_rows": len(rows),
            "source_as_of": load["source_as_of"],
        }
