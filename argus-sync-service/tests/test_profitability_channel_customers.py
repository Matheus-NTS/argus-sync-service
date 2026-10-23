"""Testes da dimensao de clientes por canal."""

import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from features.intelligence.profitability.profitability_channel_customers import (
    prepare_channel_customers,
)


class ChannelCustomersTests(unittest.TestCase):

    def test_classification_and_columns(self):
        source = pd.DataFrame({
            "Codigo_Cliente": ["101", "102", "103", "104"],
            "Classificacao_1": ["REVENDA", "Consumidor", None, "   "],
        })

        result = prepare_channel_customers(source)

        self.assertEqual(
            list(result.columns),
            ["codigo_cliente_normalizado", "segmento"],
        )
        self.assertEqual(
            result["segmento"].tolist(),
            [
                "Atacado",
                "Varejo",
                "N\u00e3o classificados",
                "N\u00e3o classificados",
            ],
        )
        self.assertEqual(result["codigo_cliente_normalizado"].nunique(), 4)

    def test_does_not_mutate_source(self):
        source = pd.DataFrame({
            "Codigo_Cliente": ["101", "102"],
            "Classificacao_1": ["REVENDA", None],
        })
        original = source.copy(deep=True)

        prepare_channel_customers(source)

        assert_frame_equal(source, original)

    def test_duplicate_code_rejected(self):
        source = pd.DataFrame({
            "Codigo_Cliente": ["101", "101"],
            "Classificacao_1": ["REVENDA", "REVENDA"],
        })

        with self.assertRaises(ValueError):
            prepare_channel_customers(source)

    def test_conflicting_classification_rejected(self):
        source = pd.DataFrame({
            "Codigo_Cliente": ["101", "101"],
            "Classificacao_1": ["REVENDA", "Consumidor"],
        })

        with self.assertRaises(ValueError):
            prepare_channel_customers(source)

    def test_missing_code_rejected(self):
        source = pd.DataFrame({
            "Codigo_Cliente": [None],
            "Classificacao_1": ["REVENDA"],
        })

        with self.assertRaises(ValueError):
            prepare_channel_customers(source)

    def test_missing_required_column_rejected(self):
        source = pd.DataFrame({
            "Codigo_Cliente": ["101"],
        })

        with self.assertRaises(KeyError):
            prepare_channel_customers(source)


if __name__ == "__main__":
    unittest.main()
