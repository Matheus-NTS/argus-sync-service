"""Testes do motor analitico Atacado x Varejo."""

import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from features.intelligence.profitability.profitability_channel_analytics import (
    build_channel_overview,
)


class ChannelAnalyticsTests(unittest.TestCase):

    def sample(self):
        return pd.DataFrame({
            "segmento": [
                "Atacado", "Atacado", "Varejo",
                "Varejo", 'Não classificados',
            ],
            "elegivel_kpi": [True, True, True, False, True],
            "faturamento_analisavel": [100.0, 300.0, 200.0, None, 50.0],
            "custo_analisavel": [60.0, 150.0, 100.0, None, 25.0],
            "lucro_analisavel": [40.0, 150.0, 100.0, None, 25.0],
        })

    def test_financial_totals_and_ratios(self):
        result = build_channel_overview(self.sample())
        wholesale = result.set_index("segmento").loc["Atacado"]

        self.assertEqual(wholesale["ocorrencias"], 2)
        self.assertAlmostEqual(wholesale["faturamento_analisavel"], 400)
        self.assertAlmostEqual(wholesale["custo_analisavel"], 210)
        self.assertAlmostEqual(wholesale["lucro_analisavel"], 190)
        self.assertAlmostEqual(wholesale["margem_percentual"], 47.5)
        self.assertAlmostEqual(
            wholesale["markup_percentual"], 190 / 210 * 100
        )

    def test_other_segments_and_eligibility(self):
        result = build_channel_overview(self.sample()).set_index("segmento")

        self.assertEqual(result.loc["Varejo", "ocorrencias"], 1)
        self.assertEqual(
            result.loc["Varejo", "faturamento_analisavel"], 200
        )
        self.assertEqual(
            result.loc["Não classificados", "faturamento_analisavel"], 50
        )

    def test_does_not_mutate_input(self):
        data = self.sample()
        original = data.copy(deep=True)

        build_channel_overview(data)

        assert_frame_equal(data, original)

    def test_rejects_invalid_segment(self):
        data = self.sample()
        data.loc[0, "segmento"] = "Outro"

        with self.assertRaisesRegex(ValueError, "Segmento invalido"):
            build_channel_overview(data)

    def test_rejects_missing_eligible_financial_value(self):
        data = self.sample()
        data.loc[0, "lucro_analisavel"] = None

        with self.assertRaisesRegex(ValueError, "ausente"):
            build_channel_overview(data)

    def test_rejects_nonfinite_financial_value(self):
        data = self.sample()
        data.loc[0, "custo_analisavel"] = float("inf")

        with self.assertRaisesRegex(ValueError, "nao finito"):
            build_channel_overview(data)


if __name__ == "__main__":
    unittest.main()
