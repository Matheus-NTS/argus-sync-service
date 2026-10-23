import pandas as pd
import unittest
from pandas.testing import assert_frame_equal

from features.intelligence.profitability.profitability_channel_detail import (
    build_channel_detail,
)


def sample_dataset():
    return pd.DataFrame({
        "numero_pedido": ["100", "100", "101", "102"],
        "codigo_produto": ["A", "A", "B", "C"],
        "codigo_cliente_normalizado": ["1", "1", "2", "3"],
        "elegivel_kpi": [True, True, False, True],
        "faturamento_analisavel": [100.0, 50.0, None, 200.0],
        "custo_analisavel": [60.0, 30.0, None, 100.0],
        "lucro_analisavel": [40.0, 20.0, None, 100.0],
    })


def sample_customers():
    return pd.DataFrame({
        "Codigo_Cliente": ["1", "2"],
        "Classificacao_1": ["REVENDA", "CONSUMIDOR"],
    })


def test_preserves_occurrences_and_original_dataset():
    dataset = sample_dataset()
    original = dataset.copy(deep=True)

    result = build_channel_detail(dataset, sample_customers())

    assert len(result) == 4
    assert result["numero_pedido"].tolist() == [
        "100", "100", "101", "102"
    ]
    assert result["segmento"].tolist() == [
        "Atacado", "Atacado", "Varejo", "Não classificados"
    ]

    assert_frame_equal(dataset, original)


def test_rejects_conflicting_classifications():
    customers = pd.DataFrame({
        "Codigo_Cliente": ["1", "1"],
        "Classificacao_1": ["REVENDA", "CONSUMIDOR"],
    })

    with unittest.TestCase().assertRaisesRegex(ValueError, "conflitantes"):
        build_channel_detail(sample_dataset(), customers)


def test_rejects_existing_segment_column():
    dataset = sample_dataset()
    dataset["segmento"] = "Atacado"

    with unittest.TestCase().assertRaisesRegex(ValueError, "já contém segmento"):
        build_channel_detail(dataset, sample_customers())


def test_preserves_financial_values_and_nulls():
    dataset = sample_dataset()
    result = build_channel_detail(dataset, sample_customers())

    for column in (
        "faturamento_analisavel",
        "custo_analisavel",
        "lucro_analisavel",
    ):
        assert result[column].equals(dataset[column])


class TestProfitabilityChannelDetail(unittest.TestCase):
    def test_preserves_financial_values_and_nulls(self):
        test_preserves_financial_values_and_nulls()

    def test_preserves_occurrences_and_original_dataset(self):
        test_preserves_occurrences_and_original_dataset()

    def test_rejects_conflicting_classifications(self):
        test_rejects_conflicting_classifications()

    def test_rejects_existing_segment_column(self):
        test_rejects_existing_segment_column()
