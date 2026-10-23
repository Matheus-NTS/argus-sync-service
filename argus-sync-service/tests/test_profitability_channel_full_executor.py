from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock, patch

import pandas as pd

from features.intelligence.profitability import (
    profitability_channel_executor as executor,
)


class ChannelFullExecutorTests(TestCase):

    @patch.object(executor, "build_channel_detail")
    @patch.object(executor, "build_channel_daily")
    @patch.object(executor, "read_customer_classifications")
    @patch.object(executor, "ProfitabilityDataset")
    @patch.object(executor, "ProdutoTransformer")
    @patch.object(executor, "CommercialAdjustmentTransformer")
    @patch.object(executor, "PedidoTransformer")
    @patch.object(executor, "ProdutoExtractor")
    @patch.object(executor, "PedidoExtractor")
    def test_full_snapshot_uses_one_extraction_and_preserves_inputs(
        self,
        pedido_extractor,
        produto_extractor,
        pedido_transformer,
        adjustment_transformer,
        produto_transformer,
        profitability_dataset,
        read_customers,
        build_daily,
        build_detail,
    ):
        sql_connector = Mock()

        dataset = pd.DataFrame({
            "data_venda": ["2026-10-01", "2026-10-01", None],
            "numero_pedido": ["100", "100", "101"],
            "valor": [100.0, 50.0, 200.0],
        })

        profitability_dataset.return_value.build.return_value = dataset

        customers = pd.DataFrame({"Codigo_Cliente": ["1"]})
        read_customers.return_value = customers

        expected_daily = object()
        expected_detail = object()

        build_daily.return_value = expected_daily
        build_detail.return_value = expected_detail

        before = datetime.now(timezone.utc)

        daily, detail, source_as_of = (
            executor.build_profitability_channel_full_snapshot(sql_connector)
        )

        after = datetime.now(timezone.utc)

        self.assertIs(daily, expected_daily)
        self.assertIs(detail, expected_detail)
        self.assertLessEqual(before, source_as_of)
        self.assertLessEqual(source_as_of, after)

        pedido_extractor.assert_called_once_with(sql_connector)
        produto_extractor.assert_called_once_with(sql_connector)

        pedido_extractor.return_value.extract.assert_called_once_with()
        produto_extractor.return_value.extract.assert_called_once_with()

        pedido_transformer.return_value.filter_revenue_orders.assert_called_once()
        adjustment_transformer.return_value.apply.assert_called_once()
        produto_transformer.return_value.prepare.assert_called_once()

        profitability_dataset.return_value.build.assert_called_once()
        read_customers.assert_called_once_with(sql_connector)

        build_daily.assert_called_once()
        build_detail.assert_called_once()

        daily_dataset, daily_customers = build_daily.call_args.args
        detail_dataset, detail_customers = build_detail.call_args.args

        self.assertEqual(len(daily_dataset), 2)
        self.assertEqual(len(detail_dataset), 2)
        self.assertEqual(len(dataset), 3)

        pd.testing.assert_frame_equal(daily_dataset, detail_dataset)

        self.assertIs(daily_customers, customers)
        self.assertIs(detail_customers, customers)


if __name__ == "__main__":
    import unittest
    unittest.main()
