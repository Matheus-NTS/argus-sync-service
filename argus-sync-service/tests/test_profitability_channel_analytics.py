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




class ChannelGroupedTests(unittest.TestCase):

    def sample(self):
        return pd.DataFrame({
            "empresa_key": ["RJ", "RJ", "SP", "SP", "RJ"],
            "vendedor": ["Ana", "Bruno", "Ana", None, "Ana"],
            "segmento": [
                "Atacado", "Atacado", "Varejo",
                "Varejo", "Atacado",
            ],
            "elegivel_kpi": [True, True, True, True, False],
            "faturamento_analisavel": [100.0, 300.0, 200.0, 50.0, None],
            "custo_analisavel": [60.0, 150.0, 100.0, 25.0, None],
            "lucro_analisavel": [40.0, 150.0, 100.0, 25.0, None],
        })

    def test_company_and_seller_reconcile_with_overview(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
        )

        data = self.sample()
        general = build_channel_overview(data)

        for dimensions in (
            ("empresa_key",),
            ("vendedor",),
            ("empresa_key", "vendedor"),
        ):
            grouped = build_channel_grouped(data, dimensions)

            for column in (
                "faturamento_analisavel",
                "custo_analisavel",
                "lucro_analisavel",
            ):
                self.assertAlmostEqual(
                    grouped[column].sum(),
                    general[column].sum(),
                )

            self.assertEqual(
                grouped["ocorrencias"].sum(),
                general["ocorrencias"].sum(),
            )

    def test_missing_seller_is_preserved(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
        )

        result = build_channel_grouped(
            self.sample(), ("empresa_key", "vendedor")
        )

        missing = result.loc[
            result["vendedor"].isna()
            & result["segmento"].eq("Varejo")
        ]

        self.assertEqual(len(missing), 1)
        self.assertEqual(
            missing.iloc[0]["faturamento_analisavel"], 50
        )

    def test_grouped_does_not_mutate_input(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
        )

        data = self.sample()
        original = data.copy(deep=True)

        build_channel_grouped(data, ("empresa_key", "vendedor"))

        assert_frame_equal(data, original)

    def test_invalid_dimensions_are_rejected(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
        )

        data = self.sample()

        for dimensions in (
            (),
            ("segmento",),
            ("empresa_key", "empresa_key"),
        ):
            with self.subTest(dimensions=dimensions):
                with self.assertRaises(ValueError):
                    build_channel_grouped(data, dimensions)




class ChannelPeriodTests(unittest.TestCase):

    def sample(self):
        return pd.DataFrame({
            "data_venda": [
                "2025-12-29",
                "2025-12-31",
                "2026-01-01",
                "2026-01-04",
                "2026-01-05",
                "2026-02-01",
            ],
            "valor": [10, 20, 30, 40, 50, 60],
        })

    def test_month_and_year_boundaries(self):
        from datetime import date
        from features.intelligence.profitability.profitability_channel_analytics import (
            prepare_channel_periods,
        )

        result = prepare_channel_periods(self.sample())

        self.assertEqual(
            result["periodo_mensal"].tolist(),
            [
                date(2025, 12, 1),
                date(2025, 12, 1),
                date(2026, 1, 1),
                date(2026, 1, 1),
                date(2026, 1, 1),
                date(2026, 2, 1),
            ],
        )

        self.assertEqual(
            result["periodo_semanal"].tolist(),
            [
                date(2025, 12, 29),
                date(2025, 12, 29),
                date(2025, 12, 29),
                date(2025, 12, 29),
                date(2026, 1, 5),
                date(2026, 1, 26),
            ],
        )

    def test_preserves_original_data(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            prepare_channel_periods,
        )

        data = self.sample()
        original = data.copy(deep=True)

        result = prepare_channel_periods(data)

        assert_frame_equal(data, original)
        self.assertEqual(len(result), len(data))
        self.assertEqual(
            list(result.columns),
            list(data.columns) + ["periodo_mensal", "periodo_semanal"],
        )

    def test_invalid_and_missing_dates(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            prepare_channel_periods,
        )

        for invalid in ("data-invalida", None):
            with self.subTest(invalid=invalid):
                data = self.sample()
                data.loc[0, "data_venda"] = invalid

                with self.assertRaises((ValueError, TypeError)):
                    prepare_channel_periods(data)

    def test_rejects_existing_period_columns(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            prepare_channel_periods,
        )

        data = self.sample()
        data["periodo_mensal"] = None

        with self.assertRaises(ValueError):
            prepare_channel_periods(data)




class ChannelTemporalReconciliationTests(unittest.TestCase):

    def sample(self):
        return pd.DataFrame({
            "data_venda": [
                "2025-12-29",
                "2025-12-31",
                "2026-01-01",
                "2026-01-05",
                "2026-02-01",
                "2026-02-02",
            ],
            "empresa_key": ["RJ", "RJ", "SP", "SP", "RJ", "RJ"],
            "vendedor": ["Ana", "Bruno", "Ana", None, "Ana", "Bruno"],
            "segmento": [
                "Atacado", "Varejo", "Atacado",
                "Varejo", "Atacado", "Varejo",
            ],
            "elegivel_kpi": [True, True, True, True, True, False],
            "faturamento_analisavel": [
                100.0, 200.0, 300.0, 400.0, 500.0, None
            ],
            "custo_analisavel": [
                60.0, 100.0, 180.0, 200.0, 250.0, None
            ],
            "lucro_analisavel": [
                40.0, 100.0, 120.0, 200.0, 250.0, None
            ],
        })

    def test_temporal_groupings_reconcile_by_segment(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
            prepare_channel_periods,
        )

        data = prepare_channel_periods(self.sample())
        general = build_channel_overview(data).set_index("segmento")

        combinations = (
            ("periodo_mensal",),
            ("periodo_semanal",),
            ("periodo_mensal", "empresa_key"),
            ("periodo_semanal", "vendedor"),
            ("periodo_mensal", "empresa_key", "vendedor"),
            ("periodo_semanal", "empresa_key", "vendedor"),
        )

        for dimensions in combinations:
            with self.subTest(dimensions=dimensions):
                grouped = build_channel_grouped(data, dimensions)
                totals = grouped.groupby("segmento")[
                    [
                        "ocorrencias",
                        "faturamento_analisavel",
                        "custo_analisavel",
                        "lucro_analisavel",
                    ]
                ].sum()

                for segment in general.index:
                    for column in totals.columns:
                        self.assertAlmostEqual(
                            totals.loc[segment, column],
                            general.loc[segment, column],
                            places=6,
                        )

    def test_week_crossing_year_keeps_same_monday(self):
        from datetime import date
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
            prepare_channel_periods,
        )

        data = prepare_channel_periods(self.sample())
        weekly = build_channel_grouped(data, ("periodo_semanal",))

        first_week = weekly.loc[
            weekly["periodo_semanal"].eq(date(2025, 12, 29))
        ]

        self.assertEqual(first_week["ocorrencias"].sum(), 3)
        self.assertAlmostEqual(
            first_week["faturamento_analisavel"].sum(), 600.0
        )

    def test_ratios_are_calculated_from_group_totals(self):
        from datetime import date
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
            prepare_channel_periods,
        )

        data = prepare_channel_periods(self.sample())
        monthly = build_channel_grouped(data, ("periodo_mensal",))

        january_retail = monthly.loc[
            monthly["periodo_mensal"].eq(date(2026, 1, 1))
            & monthly["segmento"].eq("Varejo")
        ].iloc[0]

        self.assertAlmostEqual(january_retail["margem_percentual"], 50.0)
        self.assertAlmostEqual(january_retail["markup_percentual"], 100.0)

    def test_temporal_grouping_preserves_original(self):
        from features.intelligence.profitability.profitability_channel_analytics import (
            build_channel_grouped,
            prepare_channel_periods,
        )

        original = self.sample()
        before = original.copy(deep=True)

        prepared = prepare_channel_periods(original)
        build_channel_grouped(
            prepared,
            ("periodo_semanal", "empresa_key", "vendedor"),
        )

        assert_frame_equal(original, before)


if __name__ == "__main__":
    unittest.main()
