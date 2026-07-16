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

    if value is None or pd.isna(value):
        return "R$ 0,00"

    formatted = f"{float(value):,.2f}"

    return (
        "R$ "
        + formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def format_percent(value):

    if value is None or pd.isna(value):
        return "-"

    return f"{float(value):.2f}%"


def weighted_metrics(df):

    valid = df[df["custo_valido"]].copy()

    faturamento_total = float(
        df["faturamento"].sum()
    )

    faturamento_valido = float(
        valid["faturamento"].sum()
    )

    custo_total = float(
        valid["custo_total"].sum()
    )

    lucro_total = float(
        valid["lucro_bruto"].sum()
    )

    margem = (
        lucro_total / faturamento_valido * 100
        if faturamento_valido > 0
        else None
    )

    markup = (
        lucro_total / custo_total * 100
        if custo_total > 0
        else None
    )

    cobertura = (
        faturamento_valido / faturamento_total * 100
        if faturamento_total > 0
        else None
    )

    return {
        "faturamento_total": faturamento_total,
        "faturamento_valido": faturamento_valido,
        "custo_total": custo_total,
        "lucro_total": lucro_total,
        "margem": margem,
        "markup": markup,
        "cobertura": cobertura,
    }


def print_company_summary(dataset):

    print()
    print("=" * 80)
    print("1. RENTABILIDADE POR EMPRESA")
    print("=" * 80)

    rows = []

    for empresa, df_empresa in dataset.groupby(
        "empresa_key",
        dropna=False
    ):

        metrics = weighted_metrics(df_empresa)

        rows.append({
            "Empresa": empresa or "Não informado",
            "Faturamento total": metrics["faturamento_total"],
            "Faturamento analisável": metrics["faturamento_valido"],
            "Cobertura %": metrics["cobertura"],
            "Custo": metrics["custo_total"],
            "Lucro bruto": metrics["lucro_total"],
            "Margem %": metrics["margem"],
            "Markup %": metrics["markup"],
            "Linhas": len(df_empresa),
            "Sem custo": int(
                (~df_empresa["custo_valido"]).sum()
            ),
        })

    company_df = pd.DataFrame(rows)

    company_df = company_df.sort_values(
        "Faturamento total",
        ascending=False
    )

    display_df = company_df.copy()

    for column in [
        "Faturamento total",
        "Faturamento analisável",
        "Custo",
        "Lucro bruto",
    ]:
        display_df[column] = display_df[column].apply(
            format_currency
        )

    for column in [
        "Cobertura %",
        "Margem %",
        "Markup %",
    ]:
        display_df[column] = display_df[column].apply(
            format_percent
        )

    print(
        display_df.to_string(
            index=False
        )
    )


def print_missing_cost_by_company(dataset):

    print()
    print("=" * 80)
    print("2. FATURAMENTO SEM CUSTO POR EMPRESA")
    print("=" * 80)

    missing = dataset[
        ~dataset["custo_valido"]
    ].copy()

    if missing.empty:
        print("Nenhuma venda sem custo válido.")
        return

    summary = (
        missing
        .groupby(
            [
                "empresa_key",
                "status_custo",
            ],
            dropna=False
        )
        .agg(
            linhas=("codigo_produto", "size"),
            faturamento=("faturamento", "sum"),
            produtos=("codigo_produto", "nunique"),
        )
        .reset_index()
        .sort_values(
            "faturamento",
            ascending=False
        )
    )

    summary["faturamento"] = summary[
        "faturamento"
    ].apply(format_currency)

    print(
        summary.to_string(
            index=False
        )
    )


def print_top_missing_products(dataset):

    print()
    print("=" * 80)
    print("3. PRODUTOS SEM CUSTO — MAIOR FATURAMENTO")
    print("=" * 80)

    missing = dataset[
        ~dataset["custo_valido"]
    ].copy()

    if missing.empty:
        print("Nenhum produto sem custo válido.")
        return

    summary = (
        missing
        .groupby(
            [
                "empresa_key",
                "codigo_produto",
                "produto",
                "status_custo",
            ],
            dropna=False
        )
        .agg(
            linhas=("codigo_produto", "size"),
            pedidos=("numero_pedido", "nunique"),
            quantidade=("quantidade", "sum"),
            faturamento=("faturamento", "sum"),
        )
        .reset_index()
        .sort_values(
            "faturamento",
            ascending=False
        )
        .head(30)
    )

    summary["faturamento"] = summary[
        "faturamento"
    ].apply(format_currency)

    print(
        summary.to_string(
            index=False
        )
    )


def print_negative_profit(dataset):

    print()
    print("=" * 80)
    print("4. MAIORES PREJUÍZOS POR PRODUTO")
    print("=" * 80)

    negative = dataset[
        dataset["custo_valido"]
        & (dataset["lucro_bruto"] < 0)
    ].copy()

    if negative.empty:
        print("Nenhuma venda com prejuízo.")
        return

    summary = (
        negative
        .groupby(
            [
                "empresa_key",
                "codigo_produto",
                "produto",
            ],
            dropna=False
        )
        .agg(
            linhas=("codigo_produto", "size"),
            pedidos=("numero_pedido", "nunique"),
            quantidade=("quantidade", "sum"),
            faturamento=("faturamento", "sum"),
            custo=("custo_total", "sum"),
            lucro=("lucro_bruto", "sum"),
        )
        .reset_index()
    )

    summary["margem_percentual"] = summary.apply(
        lambda row: (
            row["lucro"] / row["faturamento"] * 100
            if row["faturamento"] > 0
            else None
        ),
        axis=1
    )

    summary = summary.sort_values(
        "lucro",
        ascending=True
    ).head(30)

    for column in [
        "faturamento",
        "custo",
        "lucro",
    ]:
        summary[column] = summary[
            column
        ].apply(format_currency)

    summary["margem_percentual"] = summary[
        "margem_percentual"
    ].apply(format_percent)

    print(
        summary.to_string(
            index=False
        )
    )


def print_recent_periods(dataset):

    print()
    print("=" * 80)
    print("5. COMPARAÇÃO POR PERÍODO")
    print("=" * 80)

    valid_dates = dataset[
        dataset["data_venda"].notna()
    ].copy()

    if valid_dates.empty:
        print("Nenhuma data válida.")
        return

    reference_date = valid_dates[
        "data_venda"
    ].max().date()

    current_year_start = pd.Timestamp(
        year=reference_date.year,
        month=1,
        day=1
    )

    previous_year_same_day = pd.Timestamp(
        year=reference_date.year - 1,
        month=reference_date.month,
        day=reference_date.day
    )

    previous_year_start = pd.Timestamp(
        year=reference_date.year - 1,
        month=1,
        day=1
    )

    last_30_start = (
        pd.Timestamp(reference_date)
        - pd.Timedelta(days=29)
    )

    current_month_start = pd.Timestamp(
        year=reference_date.year,
        month=reference_date.month,
        day=1
    )

    periods = {
        "Histórico completo": valid_dates,
        "Ano atual": valid_dates[
            valid_dates["data_venda"]
            >= current_year_start
        ],
        "Mesmo período ano anterior": valid_dates[
            (
                valid_dates["data_venda"]
                >= previous_year_start
            )
            & (
                valid_dates["data_venda"]
                <= previous_year_same_day
            )
        ],
        "Mês atual": valid_dates[
            valid_dates["data_venda"]
            >= current_month_start
        ],
        "Últimos 30 dias": valid_dates[
            valid_dates["data_venda"]
            >= last_30_start
        ],
    }

    rows = []

    for label, df_period in periods.items():

        metrics = weighted_metrics(df_period)

        rows.append({
            "Período": label,
            "Linhas": len(df_period),
            "Faturamento": metrics["faturamento_total"],
            "Faturamento analisável": metrics["faturamento_valido"],
            "Cobertura %": metrics["cobertura"],
            "Custo": metrics["custo_total"],
            "Lucro bruto": metrics["lucro_total"],
            "Margem %": metrics["margem"],
            "Markup %": metrics["markup"],
        })

    period_df = pd.DataFrame(rows)

    display_df = period_df.copy()

    for column in [
        "Faturamento",
        "Faturamento analisável",
        "Custo",
        "Lucro bruto",
    ]:
        display_df[column] = display_df[
            column
        ].apply(format_currency)

    for column in [
        "Cobertura %",
        "Margem %",
        "Markup %",
    ]:
        display_df[column] = display_df[
            column
        ].apply(format_percent)

    print(
        display_df.to_string(
            index=False
        )
    )


def print_top_profit_products(dataset):

    print()
    print("=" * 80)
    print("6. PRODUTOS COM MAIOR LUCRO BRUTO")
    print("=" * 80)

    valid = dataset[
        dataset["custo_valido"]
    ].copy()

    summary = (
        valid
        .groupby(
            [
                "codigo_produto",
                "produto",
            ],
            dropna=False
        )
        .agg(
            pedidos=("numero_pedido", "nunique"),
            quantidade=("quantidade", "sum"),
            faturamento=("faturamento", "sum"),
            custo=("custo_total", "sum"),
            lucro=("lucro_bruto", "sum"),
        )
        .reset_index()
    )

    summary["margem_percentual"] = summary.apply(
        lambda row: (
            row["lucro"] / row["faturamento"] * 100
            if row["faturamento"] > 0
            else None
        ),
        axis=1
    )

    summary = summary.sort_values(
        "lucro",
        ascending=False
    ).head(20)

    for column in [
        "faturamento",
        "custo",
        "lucro",
    ]:
        summary[column] = summary[
            column
        ].apply(format_currency)

    summary["margem_percentual"] = summary[
        "margem_percentual"
    ].apply(format_percent)

    print(
        summary.to_string(
            index=False
        )
    )


def print_high_revenue_low_margin(dataset):

    print()
    print("=" * 80)
    print("7. ALTO FATURAMENTO COM MARGEM BAIXA")
    print("=" * 80)

    valid = dataset[
        dataset["custo_valido"]
    ].copy()

    summary = (
        valid
        .groupby(
            [
                "codigo_produto",
                "produto",
            ],
            dropna=False
        )
        .agg(
            pedidos=("numero_pedido", "nunique"),
            quantidade=("quantidade", "sum"),
            faturamento=("faturamento", "sum"),
            custo=("custo_total", "sum"),
            lucro=("lucro_bruto", "sum"),
        )
        .reset_index()
    )

    summary["margem_percentual"] = summary.apply(
        lambda row: (
            row["lucro"] / row["faturamento"] * 100
            if row["faturamento"] > 0
            else None
        ),
        axis=1
    )

    revenue_cutoff = summary[
        "faturamento"
    ].quantile(0.75)

    attention = summary[
        (summary["faturamento"] >= revenue_cutoff)
        & (summary["margem_percentual"] < 15)
    ].copy()

    attention = attention.sort_values(
        [
            "faturamento",
            "margem_percentual",
        ],
        ascending=[
            False,
            True,
        ]
    ).head(30)

    if attention.empty:
        print(
            "Nenhum produto de alto faturamento "
            "com margem abaixo de 15%."
        )
        return

    for column in [
        "faturamento",
        "custo",
        "lucro",
    ]:
        attention[column] = attention[
            column
        ].apply(format_currency)

    attention["margem_percentual"] = attention[
        "margem_percentual"
    ].apply(format_percent)

    print(
        attention.to_string(
            index=False
        )
    )


def main():

    print("=" * 80)
    print("DIAGNÓSTICO FINAL — RENTABILIDADE")
    print("=" * 80)

    sql_connector = SQLServerConnector()

    pedidos_raw = PedidoExtractor(
        sql_connector
    ).extract()

    produtos_raw = ProdutoExtractor(
        sql_connector
    ).extract()

    pedidos = (
        PedidoTransformer()
        .filter_revenue_orders(
            pedidos_raw
        )
    )

    produtos = (
        ProdutoTransformer()
        .prepare(
            produtos_raw
        )
    )

    dataset = (
        ProfitabilityDataset()
        .build(
            pedidos,
            produtos
        )
    )

    print()
    print(
        f"Data de referência: "
        f"{dataset['data_venda'].max().date()}"
    )

    print(
        f"Linhas analisadas: "
        f"{len(dataset):,}"
    )

    print_company_summary(dataset)
    print_missing_cost_by_company(dataset)
    print_top_missing_products(dataset)
    print_negative_profit(dataset)
    print_recent_periods(dataset)
    print_top_profit_products(dataset)
    print_high_revenue_low_margin(dataset)

    print()
    print("=" * 80)
    print("DIAGNÓSTICO FINALIZADO")
    print("=" * 80)


if __name__ == "__main__":
    main()