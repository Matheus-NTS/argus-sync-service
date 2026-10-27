"""Testes do contrato de extensao da Rentabilidade."""

import unittest
from unittest.mock import Mock

import pandas as pd

from pipelines.profitability_pipeline import ProfitabilityPipeline


class ProfitabilityDatasetCallbackTests(unittest.TestCase):

    def test_callback_is_disabled_by_default(self):
        pipeline = ProfitabilityPipeline(
            Mock(),
            Mock(),
        )

        self.assertIsNone(pipeline.on_dataset_ready)

    def test_callback_receives_independent_dataset(self):
        pipeline = ProfitabilityPipeline(
            Mock(),
            Mock(),
        )

        dataset = pd.DataFrame({
            "numero_pedido": [1001],
            "faturamento_analisavel": [500.0],
        })

        received = []

        def callback(frame):
            received.append(frame)
            frame.loc[0, "faturamento_analisavel"] = 0.0

        pipeline.on_dataset_ready = callback

        # Replica o contrato do ponto de extensao.
        pipeline.on_dataset_ready(dataset.copy())

        self.assertEqual(len(received), 1)
        self.assertEqual(
            dataset.loc[0, "faturamento_analisavel"],
            500.0,
        )


if __name__ == "__main__":
    unittest.main()
