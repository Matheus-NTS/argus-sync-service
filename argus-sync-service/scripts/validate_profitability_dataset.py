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


def format_currency(value):

    formatted = f"{float(value):,.2f}"

    return (
        "R$ "
        + formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def main():

    print("=" * 60)
    print("VALIDAÇÃO — RENTABILIDADE")
    print("=" * 60)

    sql_connector = SQLServerConnector()

    pedidos_raw = PedidoExtractor(
        sql_connector
    ).extract()

    produtos_raw = ProdutoExtractor(
        sql_connector
    ).extract()

    pedidos = PedidoTransformer().filter_revenue_orders(
        pedidos_raw
    )

    produtos = ProdutoTransformer().prepare(
        produtos_raw
    )

    dataset = ProfitabilityDataset().build(
        pedidos,
        produtos
    )

    total_rows = len(dataset)
    valid_rows = int(dataset["custo_valido"].sum())
    invalid_rows = total_rows - valid_rows

    faturamento_total = float(
        dataset["faturamento"].sum()
    )

    faturamento_valido = float(
        dataset.loc[
            dataset["custo_valido"],
            "faturamento"
        ].sum()
    )

    custo_total = float(
        dataset["custo_total"].sum()
    )

    lucro_total = float(
        dataset["lucro_bruto"].sum()
    )

    margem_ponderada = (
        lucro_total / faturamento_valido * 100
        if faturamento_valido > 0
        else 0
    )

    markup_ponderado = (
        lucro_total / custo_total * 100
        if custo_total > 0
        else 0
    )

    cobertura_linhas = (
        valid_rows / total_rows * 100
        if total_rows > 0
        else 0
    )

    cobertura_faturamento = (
        faturamento_valido / faturamento_total * 100
        if faturamento_total > 0
        else 0
    )

    print()
    print(f"Linhas concretizadas: {total_rows:,}")
    print(f"Linhas com custo válido: {valid_rows:,}")
    print(f"Linhas sem custo válido: {invalid_rows:,}")
    print(f"Cobertura das linhas: {cobertura_linhas:.2f}%")
    print(
        "Cobertura do faturamento: "
        f"{cobertura_faturamento:.2f}%"
    )

    print()
    print(f"Faturamento total: {format_currency(faturamento_total)}")
    print(f"Faturamento analisável: {format_currency(faturamento_valido)}")
    print(f"Custo total válido: {format_currency(custo_total)}")
    print(f"Lucro bruto válido: {format_currency(lucro_total)}")
    print(f"Margem ponderada: {margem_ponderada:.2f}%")
    print(f"Markup ponderado: {markup_ponderado:.2f}%")

    print()
    print("STATUS DE CUSTO")
    print(
        dataset["status_custo"]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("STATUS DE RENTABILIDADE")
    print(
        dataset["status_rentabilidade"]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("AMOSTRA")
    print(
        dataset[
            [
                "empresa_key",
                "codigo_produto",
                "produto",
                "quantidade",
                "faturamento",
                "preco_custo",
                "custo_total",
                "lucro_bruto",
                "margem_percentual",
                "markup_percentual",
                "status_rentabilidade",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print()
    print("=" * 60)
    print("VALIDAÇÃO FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()