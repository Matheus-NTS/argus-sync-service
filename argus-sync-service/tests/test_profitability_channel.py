import unittest
import pandas as pd
from features.intelligence.profitability.profitability_channel import build_channel_daily


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.sales = pd.DataFrame([
            dict(data_venda="2026-09-01", empresa_key="RJ", vendedor="A", codigo_cliente_normalizado=" 10 ", elegivel_kpi=True, faturamento_analisavel=100, custo_analisavel=60, lucro_analisavel=40),
            dict(data_venda="2026-09-01", empresa_key="RJ", vendedor="A", codigo_cliente_normalizado="10", elegivel_kpi=True, faturamento_analisavel=100, custo_analisavel=60, lucro_analisavel=40),
            dict(data_venda="2026-09-02", empresa_key="RJ", vendedor="B", codigo_cliente_normalizado="20", elegivel_kpi=True, faturamento_analisavel=50, custo_analisavel=20, lucro_analisavel=30),
            dict(data_venda="2026-09-02", empresa_key="SP", vendedor="B", codigo_cliente_normalizado="30", elegivel_kpi=True, faturamento_analisavel=25, custo_analisavel=10, lucro_analisavel=15),
            dict(data_venda="2026-09-02", empresa_key="SP", vendedor="B", codigo_cliente_normalizado="40", elegivel_kpi=False, faturamento_analisavel=999, custo_analisavel=999, lucro_analisavel=0),
        ])
        self.customers = pd.DataFrame({"Codigo_Cliente": ["10", "20"], "Classificacao_1": [" revenda ", "CONSUMIDOR"]})

    def test_aggregation_and_reconciliation(self):
        out = build_channel_daily(self.sales, self.customers)
        self.assertEqual(len(out), 3)
        self.assertEqual(set(out.segmento), {"Atacado", "Varejo", "Não classificados"})
        self.assertEqual(out.faturamento_analisavel.sum(), 275)
        atacado = out.loc[out.segmento == "Atacado"].iloc[0]
        self.assertEqual(atacado.faturamento_analisavel, 200)
        self.assertAlmostEqual(atacado.margem_percentual, 40)
        self.assertAlmostEqual(atacado.markup_percentual, 100 * 80 / 120)

    def test_conflicting_classification_fails(self):
        customers = pd.concat([self.customers, pd.DataFrame([{"Codigo_Cliente": "10", "Classificacao_1": "CONSUMIDOR"}])], ignore_index=True)
        with self.assertRaises(ValueError):
            build_channel_daily(self.sales, customers)

    def test_input_is_not_mutated(self):
        before = self.sales.copy(deep=True)
        build_channel_daily(self.sales, self.customers)
        pd.testing.assert_frame_equal(before, self.sales)

    def test_missing_column_fails(self):
        with self.assertRaises(KeyError):
            build_channel_daily(self.sales.drop(columns="elegivel_kpi"), self.customers)

    def test_invalid_date_fails(self):
        sales = self.sales.copy()
        sales.loc[0, "data_venda"] = "invalid"
        with self.assertRaises(ValueError):
            build_channel_daily(sales, self.customers)


if __name__ == "__main__":
    unittest.main()
