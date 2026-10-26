"""Testes isolados da sincronizacao de clientes por canal."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from features.intelligence.profitability.profitability_channel_customers_sync import (
    sync_profitability_channel_customers,
)


MODULE = (
    "features.intelligence.profitability."
    "profitability_channel_customers_sync"
)


class ProfitabilityChannelCustomersSyncTests(unittest.TestCase):

    @patch(f"{MODULE}.ProfitabilityChannelCustomersPublisher")
    @patch(f"{MODULE}.read_customer_classifications")
    def test_valid_customers_are_published(self, read_mock, publisher_class):
        sql_connector = object()
        supabase_connector = object()

        read_mock.return_value = pd.DataFrame({
            "Codigo_Cliente": [" 001 ", "002", "003"],
            "Classificacao_1": ["REVENDA", "CONSUMIDOR FINAL", None],
        })

        publisher = publisher_class.return_value
        publisher.publish.return_value = {
            "run_id": "test-run",
            "expected_rows": 3,
        }

        result = sync_profitability_channel_customers(
            sql_connector,
            supabase_connector,
        )

        read_mock.assert_called_once_with(sql_connector)
        publisher_class.assert_called_once_with(supabase_connector)

        args, kwargs = publisher.publish.call_args
        frame = args[0]

        self.assertEqual(
            frame["codigo_cliente_normalizado"].tolist(),
            ["001", "002", "003"],
        )
        self.assertEqual(
            frame["segmento"].tolist(),
            ["Atacado", "Varejo", "N\u00e3o classificados"],
        )

        source_as_of = kwargs["source_as_of"]
        self.assertIsInstance(source_as_of, datetime)
        self.assertIsNotNone(source_as_of.tzinfo)
        self.assertLessEqual(
            source_as_of,
            datetime.now(timezone.utc),
        )
        self.assertEqual(result["expected_rows"], 3)

    @patch(f"{MODULE}.ProfitabilityChannelCustomersPublisher")
    @patch(f"{MODULE}.read_customer_classifications")
    def test_invalid_customers_block_publication(
        self, read_mock, publisher_class
    ):
        read_mock.return_value = pd.DataFrame({
            "Codigo_Cliente": ["001", "001"],
            "Classificacao_1": ["REVENDA", "REVENDA"],
        })

        with self.assertRaises(ValueError):
            sync_profitability_channel_customers(
                object(),
                object(),
            )

        publisher_class.assert_not_called()

    @patch(f"{MODULE}.ProfitabilityChannelCustomersPublisher")
    @patch(f"{MODULE}.read_customer_classifications")
    def test_read_failure_blocks_publication(
        self, read_mock, publisher_class
    ):
        read_mock.side_effect = RuntimeError("SQL unavailable")

        with self.assertRaisesRegex(RuntimeError, "SQL unavailable"):
            sync_profitability_channel_customers(
                object(),
                object(),
            )

        publisher_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
