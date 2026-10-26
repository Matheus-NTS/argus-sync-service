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
    prepared = prepare_channel_customers(customers)

    publisher = ProfitabilityChannelCustomersPublisher(
        supabase_connector
    )

    return publisher.publish(
        prepared,
        source_as_of=source_as_of,
    )
