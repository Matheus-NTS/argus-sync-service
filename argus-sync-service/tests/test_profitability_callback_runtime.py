"""Teste comportamental do callback na Rentabilidade oficial."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from pipelines.profitability_pipeline import ProfitabilityPipeline


MODULE = "pipelines.profitability_pipeline"


class ProfitabilityCallbackRuntimeTests(unittest.TestCase):

    def test_callback_runs_after_persistence_without_mutating_dataset(self):
        events = []

        dataset = pd.DataFrame({
            "data_venda": [pd.Timestamp("2026-10-20")],
            "numero_pedido": [1001],
            "faturamento_analisavel": [500.0],
        })

        pipeline = ProfitabilityPipeline(Mock(), Mock())

        pipeline._build_monthly_records = Mock(return_value=[])
        pipeline._build_overview_record = Mock(return_value={})
        pipeline._build_detail_records = Mock(return_value=[])
        pipeline._build_dimension_records = Mock(return_value=[])
        pipeline._build_risk_records = Mock(return_value=[])
        pipeline._build_recommendation_records = Mock(return_value=[])
        pipeline._build_quality_records = Mock(return_value=[])

        pipeline._save_period = Mock(
            side_effect=lambda **kwargs: events.append("save_period")
        )
        pipeline._save_monthly_snapshot = Mock(
            side_effect=lambda *args: events.append("save_monthly")
        )

        received = []

        def callback(frame):
            events.append("callback")
            received.append(frame)
            frame.loc[0, "faturamento_analisavel"] = 0.0

        pipeline.on_dataset_ready = callback

        overview = {
            "linhas_analisaveis": 1,
            "faturamento_analisavel": 500.0,
            "lucro_bruto": 200.0,
            "margem_percentual": 40.0,
            "markup_percentual": 66.67,
            "cobertura_financeira": 1.0,
            "status": "ok",
        }

        patches = [
            patch(f"{MODULE}.PedidoExtractor"),
            patch(f"{MODULE}.ProdutoExtractor"),
            patch(f"{MODULE}.PedidoTransformer"),
            patch(f"{MODULE}.CommercialAdjustmentTransformer"),
            patch(f"{MODULE}.ProdutoTransformer"),
            patch(f"{MODULE}.ProfitabilityDataset"),
            patch(f"{MODULE}.ProfitabilityOverview"),
            patch(f"{MODULE}.ProfitabilityDimensions"),
            patch(f"{MODULE}.ProfitabilityRisk"),
            patch(f"{MODULE}.ProfitabilityRecommendations"),
            patch(f"{MODULE}.ProfitabilityQuality"),
            patch(f"{MODULE}.resolve_window"),
        ]

        with (
            patches[0] as pedido_extractor,
            patches[1] as produto_extractor,
            patches[2] as pedido_transformer,
            patches[3] as adjustment_transformer,
            patches[4] as produto_transformer,
            patches[5] as dataset_builder,
            patches[6] as overview_builder,
            patches[7] as dimensions_builder,
            patches[8] as risk_builder,
            patches[9] as recommendations_builder,
            patches[10] as quality_builder,
            patches[11] as resolve_window_mock,
        ):
            pedido_extractor.return_value.extract.return_value = Mock()
            produto_extractor.return_value.extract.return_value = Mock()

            pedido_transformer.return_value.filter_revenue_orders.return_value = Mock()
            adjustment_transformer.return_value.apply.return_value = Mock()
            produto_transformer.return_value.prepare.return_value = Mock()

            dataset_builder.return_value.build.return_value = dataset

            overview_builder.return_value.build.return_value = overview
            dimensions_builder.return_value.build.return_value = Mock()
            risk_builder.return_value.build.return_value = Mock()
            recommendations_builder.return_value.build.return_value = Mock()
            quality_builder.return_value.build.return_value = Mock()

            resolve_window_mock.return_value = SimpleNamespace(
                date_from=datetime(2026, 1, 1).date(),
                date_to=datetime(2026, 12, 31).date(),
            )

            result = pipeline.run()

        self.assertTrue(events)
        self.assertEqual(events[-2:], ["save_monthly", "callback"])
        self.assertEqual(len(received), 1)

        self.assertIsNot(received[0], dataset)
        self.assertEqual(dataset.loc[0, "faturamento_analisavel"], 500.0)

        self.assertIn("periods_generated", result)
        self.assertIn("period_results", result)
        self.assertEqual(result["ytd_revenue"], 500.0)


if __name__ == "__main__":
    unittest.main()
