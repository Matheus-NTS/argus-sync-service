"""Publicador isolado do mart Atacado x Varejo.

Recebe o DataFrame diario ja calculado pelo modulo profitability_channel.
Nao executa extracoes, pipelines existentes nem exclui dados diretamente.
A RPC de publicacao exige as duas migracoes previamente aprovadas e aplicadas.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import math
import uuid

import pandas as pd

from .profitability_channel import GRAIN, FINANCIAL

LOAD_TABLE = "mart_profitability_channel_load"
STAGE_TABLE = "mart_profitability_channel_stage"
PUBLISH_RPC = "argus_publish_profitability_channel"
SEGMENTS = frozenset({"Atacado", "Varejo", "Não classificados"})


def prepare_channel_payload(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    """Valida integralmente a carga, sem mutar a entrada ou acessar banco."""
    required = GRAIN + FINANCIAL
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Carga vazia: publicacao bloqueada")

    data = frame[required].copy()
    dates = pd.to_datetime(data["data_venda"], errors="coerce", format="mixed")
    if dates.isna().any():
        raise ValueError("data_venda invalida")
    data["data_venda"] = dates.dt.date

    for col in ("empresa_key", "vendedor", "codigo_cliente_normalizado"):
        if data[col].isna().any() or not data[col].map(lambda x: isinstance(x, str) and bool(x.strip())).all():
            raise ValueError(f"Dimensao invalida: {col}")
    if data["segmento"].isna().any() or not data["segmento"].isin(SEGMENTS).all():
        raise ValueError("Segmento invalido")
    if data.duplicated(subset=GRAIN).any():
        raise ValueError("Chaves duplicadas no grain diario")

    for col in FINANCIAL:
        try:
            data[col] = pd.to_numeric(data[col], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Valor financeiro invalido: {col}") from exc
        if not data[col].map(lambda x: pd.notna(x) and math.isfinite(float(x))).all():
            raise ValueError(f"Valor financeiro nao finito: {col}")
        data[col] = data[col].astype(float)

    totals = {col: math.fsum(data[col].tolist()) for col in FINANCIAL}
    if not all(math.isfinite(x) for x in totals.values()):
        raise ValueError("Totais financeiros nao finitos")

    rows = []
    for row in data.to_dict(orient="records"):
        row["data_venda"] = row["data_venda"].isoformat()
        rows.append(row)
    return rows, {
        "expected_rows": len(rows),
        "expected_revenue": totals["faturamento_analisavel"],
        "expected_cost": totals["custo_analisavel"],
        "expected_profit": totals["lucro_analisavel"],
    }


class ProfitabilityChannelPublisher:
    """Reutiliza SupabaseConnector.insert/insert_batches e seu client RPC."""

    def __init__(self, supabase_connector, batch_size: int = 500):
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size <= 0:
            raise ValueError("batch_size deve ser inteiro positivo")
        self.supabase = supabase_connector
        self.batch_size = batch_size

    def publish(self, frame: pd.DataFrame, *, source_as_of: datetime) -> dict:
        """Publica somente mediante chamada explicita; jamais invocado automaticamente.

        Em falha de staging/RPC, o mart diario nao e alterado pelo Python.
        A carga incompleta permanece no staging para auditoria; nao tentar
        reutilizar o mesmo run_id nem realizar exclusao automatica.
        """
        if not isinstance(source_as_of, datetime) or source_as_of.tzinfo is None or source_as_of.utcoffset() is None:
            raise ValueError("source_as_of deve ser datetime com timezone")
        if source_as_of > datetime.now(timezone.utc):
            raise ValueError("source_as_of nao pode estar no futuro")

        rows, expected = prepare_channel_payload(frame)  # tudo antes da primeira escrita
        run_id = str(uuid.uuid4())
        load = {
            "run_id": run_id,
            "source_as_of": source_as_of.astimezone(timezone.utc).isoformat(),
            **expected,
        }
        try:
            self.supabase.insert(LOAD_TABLE, load)
            stage = [{"run_id": run_id, **row} for row in rows]
            self.supabase.insert_batches(STAGE_TABLE, stage, batch_size=self.batch_size)
        except Exception as exc:
            raise RuntimeError(
                "ARGUS_CHANNEL_STAGING_FAILED: "
                f"run_id={run_id}. "
                "Carga nao publicada. Consulte as tabelas "
                "mart_profitability_channel_load e "
                "mart_profitability_channel_stage antes de "
                "qualquer nova tentativa."
            ) from exc
        try:
            response = self.supabase.client.rpc(
                PUBLISH_RPC,
                {"p_run_id": run_id},
            ).execute()
        except Exception as exc:
            raise RuntimeError(
                "ARGUS_CHANNEL_PUBLICATION_UNCONFIRMED: "
                f"run_id={run_id}. "
                "O resultado da RPC e indeterminado. "
                "Consulte mart_profitability_channel_load "
                "antes de qualquer nova tentativa."
            ) from exc
        # A RPC retorna bigint com o numero de registros publicados.
        if response.data != expected["expected_rows"]:
            raise RuntimeError(
                "ARGUS_CHANNEL_PUBLICATION_UNCONFIRMED: "
                f"run_id={run_id}. "
                f"Retorno RPC inesperado: {response.data!r} "
                f"!= {expected['expected_rows']}. "
                "Consulte mart_profitability_channel_load "
                "antes de qualquer nova tentativa."
            )
        return {"run_id": run_id, **expected}
