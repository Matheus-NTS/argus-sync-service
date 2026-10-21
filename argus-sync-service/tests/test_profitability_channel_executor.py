import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pandas as pd

from features.intelligence.profitability import (
    profitability_channel_executor as executor,
)


class ChannelExecutorTests(unittest.TestCase):

    @patch.object(executor, "build_channel_daily")
    @patch.object(executor, "read_customer_classifications")
    @patch.object(executor, "ProfitabilityDataset")
    @patch.object(executor, "ProdutoTransformer")
    @patch.object(executor, "CommercialAdjustmentTransformer")
    @patch.object(executor, "PedidoTransformer")
    @patch.object(executor, "ProdutoExtractor")
    @patch.object(executor, "PedidoExtractor")
    def test_reuses_official_flow_without_publication(
        self,
        pedido_extractor,
        produto_extractor,
        pedido_transformer,
        adjustment_transformer,
        produto_transformer,
        profitability_dataset,
        read_customers,
        build_channel,
    ):
        sql_connector = Mock()

        orders_raw = object()
        products_raw = object()
        filtered_orders = object()
        adjusted_orders = object()
        prepared_products = object()

        pedido_extractor.return_value.extract.return_value = orders_raw
        produto_extractor.return_value.extract.return_value = products_raw

        pedido_transformer.return_value.filter_revenue_orders.return_value = filtered_orders
        adjustment_transformer.return_value.apply.return_value = adjusted_orders
        produto_transformer.return_value.prepare.return_value = prepared_products

        dataset = pd.DataFrame({
            "data_venda": ["2026-10-01", None],
            "valor": [100.0, 200.0],
        })
        profitability_dataset.return_value.build.return_value = dataset

        customers = pd.DataFrame({"Codigo_Cliente": ["1"]})
        read_customers.return_value = customers

        expected_channel = object()
        build_channel.return_value = expected_channel

        before = datetime.now(timezone.utc)
        result, source_as_of = executor.build_profitability_channel_snapshot(
            sql_connector
        )
        after = datetime.now(timezone.utc)

        self.assertIs(result, expected_channel)
        self.assertLessEqual(before, source_as_of)
        self.assertLessEqual(source_as_of, after)

        pedido_extractor.assert_called_once_with(sql_connector)
        produto_extractor.assert_called_once_with(sql_connector)

        pedido_transformer.return_value.filter_revenue_orders.assert_called_once_with(
            orders_raw
        )
        adjustment_transformer.return_value.apply.assert_called_once_with(
            filtered_orders
        )
        produto_transformer.return_value.prepare.assert_called_once_with(
            products_raw
        )
        profitability_dataset.return_value.build.assert_called_once_with(
            adjusted_orders, prepared_products
        )

        read_customers.assert_called_once_with(sql_connector)

        channel_input, customer_input = build_channel.call_args.args

        self.assertEqual(len(channel_input), 1)
        self.assertEqual(channel_input.iloc[0]["data_venda"], "2026-10-01")
        self.assertIs(customer_input, customers)

        self.assertEqual(len(dataset), 2)


if __name__ == "__main__":
    unittest.main()