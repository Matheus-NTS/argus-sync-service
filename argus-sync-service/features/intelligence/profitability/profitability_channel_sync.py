"""Sincronizacao isolada do agregado financeiro Atacado x Varejo."""

from features.intelligence.profitability.profitability_channel_executor import (
    build_profitability_channel_snapshot,
)
from features.intelligence.profitability.profitability_channel_publisher import (
    ProfitabilityChannelPublisher,
)


def sync_profitability_channel(
    sql_connector,
    supabase_connector,
):
    """Constroi e publica o agregado financeiro por canal."""
    channel_daily, source_as_of = (
        build_profitability_channel_snapshot(sql_connector)
    )

    publisher = ProfitabilityChannelPublisher(
        supabase_connector
    )

    return publisher.publish(
        channel_daily,
        source_as_of=source_as_of,
    )
