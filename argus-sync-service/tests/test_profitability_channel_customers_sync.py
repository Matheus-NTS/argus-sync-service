"""Testes isolados da sincronizacao de clientes por canal."""

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

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
        supabase_connector = Mock()
        supabase_connector.select_rows_paginated.return_value = []

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
                Mock(select_rows_paginated=Mock(return_value=[])),
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


    @patch(f"{MODULE}.ProfitabilityChannelCustomersPublisher")
    @patch(f"{MODULE}.read_customer_classifications")
    def test_financial_customer_without_registration_is_preserved(
        self, read_mock, publisher_class
    ):
        read_mock.return_value = pd.DataFrame({
            "Codigo_Cliente": ["4696"],
            "Classificacao_1": ["BOMBISTA"],
        })

        supabase = Mock()
        supabase.select_rows_paginated.return_value = [
            {"codigo_cliente_normalizado": "3750"},
            {"codigo_cliente_normalizado": "4696"},
        ]

        sync_profitability_channel_customers(object(), supabase)

        supabase.select_rows_paginated.assert_called_once_with(
            "mart_profitability_channel_daily",
            columns="codigo_cliente_normalizado",
            order_by="id",
        )

        frame = publisher_class.return_value.publish.call_args.args[0]
        segments = frame.set_index(
            "codigo_cliente_normalizado"
        )["segmento"].to_dict()

        self.assertEqual(segments, {
            "3750": "N\u00e3o classificados",
            "4696": "Varejo",
        })

    @patch(f"{MODULE}.ProfitabilityChannelCustomersPublisher")
    @patch(f"{MODULE}.read_customer_classifications")
    def test_current_sql_classification_takes_precedence(
        self, read_mock, publisher_class
    ):
        read_mock.return_value = pd.DataFrame({
            "Codigo_Cliente": ["4696"],
            "Classificacao_1": ["REVENDA"],
        })

        supabase = Mock()
        supabase.select_rows_paginated.return_value = [
            {"codigo_cliente_normalizado": "4696"},
        ]

        sync_profitability_channel_customers(object(), supabase)

        frame = publisher_class.return_value.publish.call_args.args[0]
        self.assertEqual(frame.iloc[0]["segmento"], "Atacado")

    @patch(f"{MODULE}.ProfitabilityChannelCustomersPublisher")
    @patch(f"{MODULE}.read_customer_classifications")
    def test_financial_read_failure_blocks_publication(
        self, read_mock, publisher_class
    ):
        read_mock.return_value = pd.DataFrame({
            "Codigo_Cliente": ["4696"],
            "Classificacao_1": ["BOMBISTA"],
        })

        supabase = Mock()
        supabase.select_rows_paginated.side_effect = RuntimeError(
            "Supabase unavailable"
        )

        with self.assertRaisesRegex(RuntimeError, "Supabase unavailable"):
            sync_profitability_channel_customers(object(), supabase)

        publisher_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
