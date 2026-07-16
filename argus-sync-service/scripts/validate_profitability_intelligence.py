import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor
from extractors.produto_extractor import ProdutoExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.produto_transformer import ProdutoTransformer

from features.intelligence.profitability.profitability_dataset import (
    ProfitabilityDataset,
)
from features.intelligence.profitability.profitability_overview import (
    ProfitabilityOverview,
)
from features.intelligence.profitability.profitability_dimensions import (
    ProfitabilityDimensions,
)
from features.intelligence.profitability.profitability_risk import (
    ProfitabilityRisk,
)
from features.intelligence.profitability.profitability_recommendations import (
    ProfitabilityRecommendations,
)


def main():

    print("=" * 80)
    print("VALIDAÇÃO — INTELIGÊNCIA DE RENTABILIDADE")
    print("=" * 80)

    connector = SQLServerConnector()

    pedidos = PedidoExtractor(connector).extract()
    pedidos = PedidoTransformer().filter_revenue_orders(pedidos)

    produtos = ProdutoExtractor(connector).extract()
    produtos = ProdutoTransformer().prepare(produtos)

    dataset = ProfitabilityDataset().build(
        pedidos,
        produtos
    )

    reference_year = dataset["data_venda"].max().year

    ytd = dataset[
        dataset["data_venda"].dt.year == reference_year
    ].copy()

    overview = ProfitabilityOverview().build(ytd)
    dimensions = ProfitabilityDimensions().build(ytd)

    risks = ProfitabilityRisk().build(
        dimensions,
        overview
    )

    recommendations = ProfitabilityRecommendations().build(
        dimensions,
        overview,
        risks
    )

    print()
    print(f"Status geral: {overview['status']}")
    print(f"Riscos encontrados: {len(risks)}")
    print(f"Recomendações: {len(recommendations)}")

    print()
    print("TOP 15 RISCOS")

    for index, item in enumerate(risks[:15], start=1):
        print(
            f"{index:>2}. "
            f"[{item['priority']}] "
            f"{item['dimension_type']} | "
            f"{item['dimension_value']} | "
            f"{item['risk_type']} | "
            f"Margem {item['margem_percentual']}"
        )

    print()
    print("RECOMENDAÇÕES")

    for index, item in enumerate(
        recommendations,
        start=1
    ):
        print(
            f"{index:>2}. "
            f"[{item['priority']}] "
            f"{item['title']} | "
            f"{item['dimension_value']}"
        )

    print()
    print("=" * 80)
    print("VALIDAÇÃO FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    main()