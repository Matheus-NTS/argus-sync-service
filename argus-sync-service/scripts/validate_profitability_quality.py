import sys
from pathlib import Path

import pandas as pd


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

    value = float(value or 0)

    formatted = f"{value:,.2f}"

    return (
        "R$ "
        + formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def calculate_metrics(df):

    eligible = df[
        df["elegivel_kpi"]
    ].copy()

    revenue = float(
        eligible["faturamento_analisavel"].sum()
    )

    cost = float(
        eligible["custo_analisavel"].sum()
    )

    profit = float(
        eligible["lucro_analisavel"].sum()
    )

    margin = (
        profit / revenue * 100
        if revenue > 0
        else 0
    )

    markup = (
        profit / cost * 100
        if cost > 0
        else 0
    )

    return {
        "rows": len(eligible),
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "margin": margin,
        "markup": markup,
    }


def main():

    print("=" * 80)
    print("VALIDAÇÃO FINAL DE QUALIDADE — RENTABILIDADE")
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
        .filter_revenue_orders(orders_raw)
    )

    products = (
        ProdutoTransformer()
        .prepare(products_raw)
    )

    dataset = (
        ProfitabilityDataset()
        .build(
            orders,
            products
        )
    )

    print()
    print(f"Linhas totais: {len(dataset):,}")
    print(
        f"Data de referência: "
        f"{dataset['data_venda'].max().date()}"
    )

    print()
    print("STATUS DA ANÁLISE")
    print(
        dataset["status_analise"]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("FATURAMENTO POR STATUS")

    status_summary = (
        dataset
        .groupby(
            "status_analise",
            dropna=False
        )
        .agg(
            linhas=("numero_pedido", "size"),
            pedidos=("numero_pedido", "nunique"),
            produtos=("codigo_produto", "nunique"),
            faturamento=("faturamento", "sum"),
        )
        .reset_index()
        .sort_values(
            "faturamento",
            ascending=False
        )
    )

    status_summary["faturamento"] = (
        status_summary["faturamento"]
        .apply(format_currency)
    )

    print(
        status_summary.to_string(
            index=False
        )
    )

    print()
    print("RESULTADO HISTÓRICO OFICIAL")

    historical = calculate_metrics(dataset)

    print(
        f"Linhas elegíveis: "
        f"{historical['rows']:,}"
    )
    print(
        f"Faturamento analisável: "
        f"{format_currency(historical['revenue'])}"
    )
    print(
        f"Custo analisável: "
        f"{format_currency(historical['cost'])}"
    )
    print(
        f"Lucro bruto estimado: "
        f"{format_currency(historical['profit'])}"
    )
    print(
        f"Margem ponderada: "
        f"{historical['margin']:.2f}%"
    )
    print(
        f"Markup ponderado: "
        f"{historical['markup']:.2f}%"
    )

    reference_date = (
        dataset["data_venda"]
        .max()
        .date()
    )

    ytd_start = pd.Timestamp(
        year=reference_date.year,
        month=1,
        day=1
    )

    ytd = dataset[
        dataset["data_venda"] >= ytd_start
    ].copy()

    ytd_metrics = calculate_metrics(ytd)

    print()
    print("RESULTADO ANO ATUAL OFICIAL")

    print(
        f"Linhas elegíveis: "
        f"{ytd_metrics['rows']:,}"
    )
    print(
        f"Faturamento analisável: "
        f"{format_currency(ytd_metrics['revenue'])}"
    )
    print(
        f"Custo analisável: "
        f"{format_currency(ytd_metrics['cost'])}"
    )
    print(
        f"Lucro bruto estimado: "
        f"{format_currency(ytd_metrics['profit'])}"
    )
    print(
        f"Margem ponderada: "
        f"{ytd_metrics['margin']:.2f}%"
    )
    print(
        f"Markup ponderado: "
        f"{ytd_metrics['markup']:.2f}%"
    )

    print()
    print("DADOS SUSPEITOS — MAIOR IMPACTO")

    suspicious = dataset[
        dataset["dado_suspeito"]
    ].copy()

    if suspicious.empty:
        print("Nenhuma anomalia financeira encontrada.")
    else:
        suspicious_summary = (
            suspicious
            .groupby(
                [
                    "empresa_key",
                    "codigo_produto",
                    "produto",
                ],
                dropna=False
            )
            .agg(
                linhas=("numero_pedido", "size"),
                pedidos=("numero_pedido", "nunique"),
                quantidade=("quantidade", "sum"),
                faturamento=("faturamento", "sum"),
                custo=("custo_total", "sum"),
                lucro=("lucro_bruto", "sum"),
            )
            .reset_index()
            .sort_values(
                "lucro",
                ascending=True
            )
            .head(20)
        )

        for column in [
            "faturamento",
            "custo",
            "lucro",
        ]:
            suspicious_summary[column] = (
                suspicious_summary[column]
                .apply(format_currency)
            )

        print(
            suspicious_summary.to_string(
                index=False
            )
        )

    print()
    print("PRODUTOS FORA DO ESCOPO")

    out_of_scope = dataset[
        dataset["produto_fora_escopo"]
    ].copy()

    out_summary = (
        out_of_scope
        .groupby(
            [
                "empresa_key",
                "codigo_produto",
                "produto",
            ],
            dropna=False
        )
        .agg(
            linhas=("numero_pedido", "size"),
            pedidos=("numero_pedido", "nunique"),
            faturamento=("faturamento", "sum"),
        )
        .reset_index()
        .sort_values(
            "faturamento",
            ascending=False
        )
        .head(20)
    )

    out_summary["faturamento"] = (
        out_summary["faturamento"]
        .apply(format_currency)
    )

    print(
        out_summary.to_string(
            index=False
        )
    )

    print()
    print("=" * 80)
    print("VALIDAÇÃO FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    main()