"""Testes do coordenador Atacado x Varejo."""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pandas as pd

from features.intelligence.profitability.profitability_channel_coordinator import (
    ProfitabilityChannelCoordinator,
)


MODULE = (
    "features.intelligence.profitability."
    "profitability_channel_coordinator"
)

SOURCE_AS_OF = datetime(
    2026, 10, 21, 14, 0, tzinfo=timezone.utc
)


class ProfitabilityChannelCoordinatorTests(unittest.TestCase):

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

    def test_success_publishes_both_from_one_classification(self):
        with (
            patch(
                f"{MODULE}.read_customer_classifications",
                return_value=self.customers,
            ) as read_mock,
            patch(
                f"{MODULE}.prepare_channel_customers",
                return_value=self.customer_frame,
            ) as prepare_mock,
            patch(
                f"{MODULE}.build_channel_daily",
                return_value=self.financial_frame,
            ) as build_mock,
            patch(
                f"{MODULE}.ProfitabilityChannelCustomersPublisher"
            ) as customer_publisher,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial_publisher,
        ):
            customer_publisher.return_value.publish.return_value = {
                "published": True,
            }

            financial_publisher.return_value.publish.return_value = {
                "published": True,
            }

            result = self.coordinator(
                self.dataset,
                source_as_of=SOURCE_AS_OF,
            )

            read_mock.assert_called_once_with(self.sql)
            prepare_mock.assert_called_once_with(
                self.customers,
                financial_frame=self.financial_frame,
            )
            build_mock.assert_called_once_with(
                self.dataset,
                self.customers,
            )

            customer_publisher.return_value.publish.assert_called_once_with(
                self.customer_frame,
                source_as_of=SOURCE_AS_OF,
            )

            financial_publisher.return_value.publish.assert_called_once_with(
                self.financial_frame,
                source_as_of=SOURCE_AS_OF,
            )

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["customers_published"])
        self.assertTrue(result["financial_published"])
        self.assertIsNone(self.coordinator.last_error)

    def test_customer_failure_blocks_financial_publication(self):
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
            ) as customer_publisher,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial_publisher,
        ):
            customer_publisher.return_value.publish.side_effect = (
                RuntimeError("Customer publication failed")
            )

            with self.assertLogs(MODULE, level="ERROR"):
                result = self.coordinator(
                    self.dataset,
                    source_as_of=SOURCE_AS_OF,
                )

            financial_publisher.assert_not_called()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_phase"], "customers")
        self.assertFalse(result["financial_published"])

    def test_financial_failure_reports_partial_publication(self):
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
            ) as customer_publisher,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial_publisher,
        ):
            customer_publisher.return_value.publish.return_value = {
                "published": True,
            }

            financial_publisher.return_value.publish.side_effect = (
                RuntimeError("Financial publication failed")
            )

            with self.assertLogs(MODULE, level="ERROR"):
                result = self.coordinator(
                    self.dataset,
                    source_as_of=SOURCE_AS_OF,
                )

        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(result["failed_phase"], "financial")
        self.assertTrue(result["customers_published"])
        self.assertFalse(result["financial_published"])

    def test_preparation_failure_does_not_publish(self):
        with (
            patch(
                f"{MODULE}.read_customer_classifications",
                side_effect=RuntimeError("SQL unavailable"),
            ),
            patch(
                f"{MODULE}.ProfitabilityChannelCustomersPublisher"
            ) as customer_publisher,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial_publisher,
        ):
            with self.assertLogs(MODULE, level="ERROR"):
                result = self.coordinator(
                    self.dataset,
                    source_as_of=SOURCE_AS_OF,
                )

            customer_publisher.assert_not_called()
            financial_publisher.assert_not_called()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_phase"], "preparation")


    def test_automatic_time_is_reused_for_both_publications(self):
        with (
            patch(
                f"{MODULE}.get_channel_source_as_of",
                return_value=SOURCE_AS_OF,
            ) as time_mock,
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
            ) as customer_publisher,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial_publisher,
        ):
            result = self.coordinator(self.dataset)

            time_mock.assert_called_once_with(self.supabase)

            self.assertEqual(
                customer_publisher.return_value.publish.call_args.kwargs[
                    "source_as_of"
                ],
                SOURCE_AS_OF,
            )

            self.assertEqual(
                financial_publisher.return_value.publish.call_args.kwargs[
                    "source_as_of"
                ],
                SOURCE_AS_OF,
            )

        self.assertEqual(result["status"], "success")

    def test_time_failure_blocks_all_publications(self):
        with (
            patch(
                f"{MODULE}.get_channel_source_as_of",
                side_effect=ValueError("ARGUS_CHANNEL_CLOCK_MISMATCH"),
            ),
            patch(
                f"{MODULE}.read_customer_classifications"
            ) as read_mock,
            patch(
                f"{MODULE}.ProfitabilityChannelCustomersPublisher"
            ) as customer_publisher,
            patch(
                f"{MODULE}.ProfitabilityChannelPublisher"
            ) as financial_publisher,
        ):
            with self.assertLogs(MODULE, level="ERROR"):
                result = self.coordinator(self.dataset)

            read_mock.assert_not_called()
            customer_publisher.assert_not_called()
            financial_publisher.assert_not_called()

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_phase"], "preparation")


if __name__ == "__main__":
    unittest.main()
