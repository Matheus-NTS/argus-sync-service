"""Coordenacao isolada das publicacoes Atacado x Varejo."""

import logging
from datetime import datetime

from features.intelligence.profitability.profitability_channel import (
    build_channel_daily,
    read_customer_classifications,
)
from features.intelligence.profitability.profitability_channel_customers import (
    prepare_channel_customers,
)
from features.intelligence.profitability.profitability_channel_customers_publisher import (
    ProfitabilityChannelCustomersPublisher,
)
from features.intelligence.profitability.profitability_channel_time import (
    get_channel_source_as_of,
)
from features.intelligence.profitability.profitability_channel_publisher import (
    ProfitabilityChannelPublisher,
)


LOGGER = logging.getLogger(__name__)


class ProfitabilityChannelCoordinator:
    """Publica dimensao e financeiro a partir da mesma classificacao."""

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase_connector = supabase_connector
        self.last_result = None
        self.last_error = None

    def __call__(
        self,
        dataset,
        *,
        source_as_of: datetime | None = None,
    ):
        result = {
            "status": "not_started",
            "customers_published": False,
            "financial_published": False,
            "customers_result": None,
            "financial_result": None,
        }

        self.last_result = result
        self.last_error = None
        phase = "preparation"

        try:
            if source_as_of is None:
                source_as_of = get_channel_source_as_of(
                    self.supabase_connector
                )

            customers = read_customer_classifications(
                self.sql_connector
            )

            customer_frame = prepare_channel_customers(
                customers
            )

            financial_frame = build_channel_daily(
                dataset,
                customers,
            )

            phase = "customers"

            customer_publisher = ProfitabilityChannelCustomersPublisher(
                self.supabase_connector
            )

            result["customers_result"] = customer_publisher.publish(
                customer_frame,
                source_as_of=source_as_of,
            )

            result["customers_published"] = True

            phase = "financial"

            financial_publisher = ProfitabilityChannelPublisher(
                self.supabase_connector
            )

            result["financial_result"] = financial_publisher.publish(
                financial_frame,
                source_as_of=source_as_of,
            )

            result["financial_published"] = True
            result["status"] = "success"

        except Exception as exc:
            self.last_error = exc

            result["status"] = (
                "partial_failure"
                if result["customers_published"]
                else "failed"
            )

            result["publication_unconfirmed"] = (
                "PUBLICATION_UNCONFIRMED" in str(exc)
            )

            result["failed_phase"] = phase
            result["error_type"] = type(exc).__name__
            result["error_message"] = str(exc)

            LOGGER.exception(
                "Falha no coordenador Atacado x Varejo "
                "(fase: %s, status: %s)",
                phase,
                result["status"],
            )

        return result
