"""Testes de publicacao sem confirmacao do canal."""

import unittest
from unittest.mock import patch

from tests.test_profitability_channel_coordinator import (
    MODULE,
    SOURCE_AS_OF,
)

from unittest.mock import Mock
import pandas as pd

from features.intelligence.profitability.profitability_channel_coordinator import (
    ProfitabilityChannelCoordinator,
)


class ChannelUnconfirmedTests(unittest.TestCase):
    def setUp(self):
        self.sql = Mock()
        self.supabase = Mock()

        self.dataset = pd.DataFrame({
            "numero_pedido": [1001],
        })
        self.customers = pd.DataFrame({
            "Codigo_Cliente": ["1"],
        })
        self.customer_frame = pd.DataFrame({
            "codigo_cliente": ["1"],
        })
        self.financial_frame = pd.DataFrame({
            "segmento": ["Atacado"],
        })

        self.coordinator = ProfitabilityChannelCoordinator(
            self.sql,
            self.supabase,
        )

    def test_unconfirmed_customer_publication(self):
        with (
            patch(
                f"{MODULE}.read_customer_classifications",
                return_value=self.customers,
            ),
            patch(
                f"{MODULE}.prepare_channel_customers",
                return_value=self.customer_frame,
            ),
            patch(
                f"{MODULE}.build_channel_daily",
                return_value=self.financial_frame,
            ),
            patch(
                f"{MODULE}.ProfitabilityChannelCustomersPublisher"
            ) as customers,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial,
        ):
            customers.return_value.publish.side_effect = (
                RuntimeError(
                    "ARGUS_CHANNEL_CUSTOMERS_PUBLICATION_UNCONFIRMED"
                )
            )

            with self.assertLogs(MODULE, level="ERROR"):
                result = self.coordinator(
                    self.dataset,
                    source_as_of=SOURCE_AS_OF,
                )

            financial.assert_not_called()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_phase"], "customers")
        self.assertTrue(result["publication_unconfirmed"])
        self.assertFalse(result["customers_published"])
        self.assertFalse(result["financial_published"])

    def test_unconfirmed_financial_publication(self):
        with (
            patch(
                f"{MODULE}.read_customer_classifications",
                return_value=self.customers,
            ),
            patch(
                f"{MODULE}.prepare_channel_customers",
                return_value=self.customer_frame,
            ),
            patch(
                f"{MODULE}.build_channel_daily",
                return_value=self.financial_frame,
            ),
            patch(
                f"{MODULE}.ProfitabilityChannelCustomersPublisher"
            ) as customers,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial,
        ):
            customers.return_value.publish.return_value = {
                "published": True
            }

            financial.return_value.publish.side_effect = (
                RuntimeError(
                    "ARGUS_CHANNEL_FINANCIAL_PUBLICATION_UNCONFIRMED"
                )
            )

            with self.assertLogs(MODULE, level="ERROR"):
                result = self.coordinator(
                    self.dataset,
                    source_as_of=SOURCE_AS_OF,
                )

        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(result["failed_phase"], "financial")
        self.assertTrue(result["publication_unconfirmed"])
        self.assertTrue(result["customers_published"])
        self.assertFalse(result["financial_published"])


if __name__ == "__main__":
    unittest.main()
