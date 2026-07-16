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


def format_currency(value):

    formatted = f"{float(value or 0):,.2f}"

    return (
        "R$ "
        + formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def main():

    print("=" * 80)
    print("VALIDAÇÃO — AGREGAÇÕES DE RENTABILIDADE")
    print("=" * 80)

    sql_connector = SQLServerConnector()

    orders_raw = PedidoExtractor(
        sql_connector
    ).extract()

    products_raw = ProdutoExtractor(
        sql_connector
    ).extract()

    orders = (
        PedidoTransformer()
        .filter_revenue_orders(
            orders_raw
        )
    )

    products = (
        ProdutoTransformer()
        .prepare(
            products_raw
        )
    )

    dataset = (
        ProfitabilityDataset()
        .build(
            orders,
            products
        )
    )

    reference_date = (
        dataset["data_venda"]
        .max()
        .date()
    )

    ytd = dataset[
        dataset["data_venda"].dt.year
        == reference_date.year
    ].copy()

    overview = ProfitabilityOverview().build(
        ytd
    )

    dimensions = ProfitabilityDimensions().build(
        ytd
    )

    print()
    print("OVERVIEW — ANO ATUAL")
    print(
        f"Faturamento: "
        f"{format_currency(overview['faturamento_analisavel'])}"
    )
    print(
        f"Custo: "
        f"{format_currency(overview['custo_analisavel'])}"
    )
    print(
        f"Lucro: "
        f"{format_currency(overview['lucro_bruto'])}"
    )
    print(
        f"Margem: "
        f"{overview['margem_percentual']:.2f}%"
    )
    print(
        f"Markup: "
        f"{overview['markup_percentual']:.2f}%"
    )
    print(
        f"Pedidos: {overview['pedidos']:,}"
    )
    print(
        f"Produtos: {overview['produtos']:,}"
    )
    print(
        f"Clientes: {overview['clientes']:,}"
    )
    print(
        f"Produtos com prejuízo: "
        f"{overview['produtos_prejuizo']:,}"
    )
    print(
        f"Produtos com margem crítica: "
        f"{overview['produtos_margem_critica']:,}"
    )
    print(
        f"Cobertura financeira: "
        f"{overview['cobertura_financeira'] * 100:.2f}%"
    )
    print(
        f"Status geral: "
        f"{overview['status']}"
    )

    print()
    print("QUANTIDADE POR DIMENSÃO")

    for dimension_type, records in dimensions.items():
        print(
            f"{dimension_type}: "
            f"{len(records):,}"
        )

    print()
    print("TOP 10 PRODUTOS POR LUCRO")

    products = sorted(
        dimensions["product"],
        key=lambda item: item["lucro"],
        reverse=True
    )[:10]

    for index, item in enumerate(
        products,
        start=1
    ):
        print(
            f"{index:>2}. "
            f"{item['dimension_value']} | "
            f"Lucro {format_currency(item['lucro'])} | "
            f"Margem "
            f"{item['margem_percentual']:.2f}%"
        )

    print()
    print("TOP 10 CLIENTES POR LUCRO")

    customers = sorted(
        dimensions["customer"],
        key=lambda item: item["lucro"],
        reverse=True
    )[:10]

    for index, item in enumerate(
        customers,
        start=1
    ):
        print(
            f"{index:>2}. "
            f"{item['dimension_value']} | "
            f"Lucro {format_currency(item['lucro'])} | "
            f"Margem "
            f"{item['margem_percentual']:.2f}%"
        )

    print()
    print("PRODUTOS COM MAIOR PREJUÍZO")

    loss_products = sorted(
        [
            item
            for item in dimensions["product"]
            if item["lucro"] < 0
        ],
        key=lambda item: item["lucro"]
    )[:10]

    for index, item in enumerate(
        loss_products,
        start=1
    ):
        print(
            f"{index:>2}. "
            f"{item['dimension_value']} | "
            f"Lucro {format_currency(item['lucro'])} | "
            f"Margem "
            f"{item['margem_percentual']:.2f}%"
        )

    print()
    print("=" * 80)
    print("VALIDAÇÃO FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    main()