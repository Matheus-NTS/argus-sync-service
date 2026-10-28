"""Sincronizacao isolada da dimensao de clientes por canal."""

from datetime import datetime, timezone

from features.intelligence.profitability.profitability_channel import (
    read_customer_classifications,
)
from features.intelligence.profitability.profitability_channel_customers import (
    prepare_channel_customers,
)
from features.intelligence.profitability.profitability_channel_customers_publisher import (
    ProfitabilityChannelCustomersPublisher,
)


def sync_profitability_channel_customers(
    sql_connector,
    supabase_connector,
):
    """Le, valida e publica a classificacao atual dos clientes."""
    source_as_of = datetime.now(timezone.utc)

    customers = read_customer_classifications(sql_connector)

    financial_rows = supabase_connector.select_rows_paginated(
        "mart_profitability_channel_daily",
        columns="codigo_cliente_normalizado",
        order_by="id",
    )

    prepared = prepare_channel_customers(customers)

    financial_codes = set()

    for row in financial_rows:
        code = row["codigo_cliente_normalizado"]

        if not isinstance(code, str) or not code.strip():
            raise ValueError("Codigo financeiro invalido")

        financial_codes.add(code)

    registered_codes = set(
        prepared["codigo_cliente_normalizado"]
    )

    missing_codes = sorted(
        financial_codes - registered_codes
    )

    if missing_codes:
        import pandas as pd

        additional = pd.DataFrame({
            "codigo_cliente_normalizado": missing_codes,
            "segmento": ["N\u00e3o classificados"] * len(missing_codes),
        })

        prepared = pd.concat(
            [prepared, additional],
            ignore_index=True,
        )

    publisher = ProfitabilityChannelCustomersPublisher(
        supabase_connector
    )

    return publisher.publish(
        prepared,
        source_as_of=source_as_of,
    )
