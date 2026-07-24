import pandas as pd

from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor

from features.intelligence.revenue.revenue_dataset import (
    RevenueDataset,
)
from features.intelligence.revenue.revenue_history import (
    RevenueHistory,
)


def format_currency(value) -> str:
    if pd.isna(value):
        return "-"

    formatted = f"{float(value):,.2f}"

    return (
        "R$ "
        + formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def format_percentage(value) -> str:
    if pd.isna(value):
        return "-"

    return f"{float(value):.2%}"


def validation_status(
    difference: float,
    tolerance: float = 0.02,
) -> str:
    return (
        "OK"
        if abs(difference) < tolerance
        else "ERRO"
    )


def main():
    print("=" * 90)
    print("VALIDAÇÃO — HISTÓRICO DE FATURAMENTO")
    print("=" * 90)

    sql_connector = SQLServerConnector()

    pedidos_raw = PedidoExtractor(
        sql_connector
    ).extract()

    pedidos = RevenueDataset().build(
        pedidos_raw
    )

    history_service = RevenueHistory()

    histories = history_service.build(
        pedidos
    )

    monthly = histories["monthly"]
    yearly = histories["yearly"]
    ytd = histories["ytd"]

    company_monthly = histories[
        "company_monthly"
    ]
    seller_monthly = histories[
        "seller_monthly"
    ]

    dataset_total = float(
        pedidos["Valor_total_Unitario"].sum()
    )

    monthly_total = float(
        monthly["faturamento"].sum()
    )

    company_total = float(
        company_monthly["faturamento"].sum()
    )

    seller_total = float(
        seller_monthly["faturamento"].sum()
    )

    print()
    print("=" * 90)
    print("TOTAIS GERAIS")
    print("=" * 90)

    print(
        "RevenueDataset:       "
        f"{format_currency(dataset_total)}"
    )
    print(
        "Histórico mensal:     "
        f"{format_currency(monthly_total)}"
    )
    print(
        "Histórico empresas:   "
        f"{format_currency(company_total)}"
    )
    print(
        "Histórico vendedores: "
        f"{format_currency(seller_total)}"
    )

    print()
    print("=" * 90)
    print("VALIDAÇÕES DE INTEGRIDADE")
    print("=" * 90)

    monthly_difference = (
        monthly_total - dataset_total
    )

    company_difference = (
        company_total - dataset_total
    )

    seller_difference = (
        seller_total - dataset_total
    )

    print(
        "Mensal x Dataset: "
        f"{validation_status(monthly_difference)} "
        f"| diferença R$ "
        f"{monthly_difference:.4f}"
    )

    print(
        "Empresas x Dataset: "
        f"{validation_status(company_difference)} "
        f"| diferença R$ "
        f"{company_difference:.4f}"
    )

    print(
        "Vendedores x Dataset: "
        f"{validation_status(seller_difference)} "
        f"| diferença R$ "
        f"{seller_difference:.4f}"
    )

    expected_month_rows = (
        monthly["ano"].nunique() * 12
    )

    calendar_status = (
        "OK"
        if len(monthly) == expected_month_rows
        else "ERRO"
    )

    print(
        "Calendário mensal: "
        f"{calendar_status} "
        f"| esperado {expected_month_rows} "
        f"| encontrado {len(monthly)}"
    )

    monthly_company_check = (
        company_monthly
        .groupby(
            [
                "ano",
                "mes",
            ],
            as_index=False,
        )["faturamento"]
        .sum()
        .rename(
            columns={
                "faturamento":
                    "faturamento_empresas",
            }
        )
        .merge(
            monthly[
                [
                    "ano",
                    "mes",
                    "faturamento",
                ]
            ],
            on=[
                "ano",
                "mes",
            ],
            how="right",
        )
    )

    monthly_company_check[
        "faturamento_empresas"
    ] = (
        monthly_company_check[
            "faturamento_empresas"
        ]
        .fillna(0)
    )

    monthly_company_check["diferenca"] = (
        monthly_company_check[
            "faturamento_empresas"
        ]
        - monthly_company_check[
            "faturamento"
        ]
    )

    max_company_month_difference = float(
        monthly_company_check[
            "diferenca"
        ]
        .abs()
        .max()
    )

    print(
        "Empresas por mês: "
        f"{validation_status(max_company_month_difference)} "
        f"| maior diferença R$ "
        f"{max_company_month_difference:.4f}"
    )

    monthly_seller_check = (
        seller_monthly
        .groupby(
            [
                "ano",
                "mes",
            ],
            as_index=False,
        )["faturamento"]
        .sum()
        .rename(
            columns={
                "faturamento":
                    "faturamento_vendedores",
            }
        )
        .merge(
            monthly[
                [
                    "ano",
                    "mes",
                    "faturamento",
                ]
            ],
            on=[
                "ano",
                "mes",
            ],
            how="right",
        )
    )

    monthly_seller_check[
        "faturamento_vendedores"
    ] = (
        monthly_seller_check[
            "faturamento_vendedores"
        ]
        .fillna(0)
    )

    monthly_seller_check["diferenca"] = (
        monthly_seller_check[
            "faturamento_vendedores"
        ]
        - monthly_seller_check[
            "faturamento"
        ]
    )

    max_seller_month_difference = float(
        monthly_seller_check[
            "diferenca"
        ]
        .abs()
        .max()
    )

    print(
        "Vendedores por mês: "
        f"{validation_status(max_seller_month_difference)} "
        f"| maior diferença R$ "
        f"{max_seller_month_difference:.4f}"
    )

    print()
    print("=" * 90)
    print("HISTÓRICO MENSAL")
    print("=" * 90)

    monthly_view = monthly.copy()

    for column in [
        "faturamento",
        "ticket_medio",
        "acumulado_ytd",
    ]:
        monthly_view[column] = (
            monthly_view[column]
            .apply(format_currency)
        )

    for column in [
        "crescimento_mom",
        "crescimento_yoy",
    ]:
        monthly_view[column] = (
            monthly_view[column]
            .apply(format_percentage)
        )

    print(
        monthly_view[
            [
                "ano_mes",
                "mes_nome",
                "faturamento",
                "pedidos",
                "ticket_medio",
                "crescimento_mom",
                "crescimento_yoy",
                "acumulado_ytd",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print("=" * 90)
    print("RESUMO ANUAL")
    print("=" * 90)

    yearly_view = yearly.copy()

    for column in [
        "faturamento",
        "ticket_medio",
        "media_mensal",
        "melhor_mes_faturamento",
        "pior_mes_faturamento",
    ]:
        yearly_view[column] = (
            yearly_view[column]
            .apply(format_currency)
        )

    yearly_view["crescimento_anual"] = (
        yearly_view["crescimento_anual"]
        .apply(format_percentage)
    )

    print(
        yearly_view[
            [
                "ano",
                "faturamento",
                "pedidos",
                "meses_com_movimento",
                "ticket_medio",
                "media_mensal",
                "melhor_mes_nome",
                "melhor_mes_faturamento",
                "pior_mes_nome",
                "pior_mes_faturamento",
                "crescimento_anual",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print("=" * 90)
    print("COMPARATIVO YTD")
    print("=" * 90)

    ytd_view = ytd.copy()

    for column in [
        "faturamento_ytd",
        "faturamento_ytd_ano_anterior",
    ]:
        ytd_view[column] = (
            ytd_view[column]
            .apply(format_currency)
        )

    ytd_view["crescimento_ytd"] = (
        ytd_view["crescimento_ytd"]
        .apply(format_percentage)
    )

    print(
        ytd_view[
            [
                "ano",
                "mes_limite",
                "faturamento_ytd",
                "faturamento_ytd_ano_anterior",
                "crescimento_ytd",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print("=" * 90)
    print("EMPRESAS ENCONTRADAS")
    print("=" * 90)

    company_summary = (
        company_monthly
        .groupby(
            "Empresa",
            as_index=False,
        )
        .agg(
            faturamento=(
                "faturamento",
                "sum",
            ),
            pedidos=(
                "pedidos",
                "sum",
            ),
        )
        .sort_values(
            "faturamento",
            ascending=False,
        )
    )

    company_summary["faturamento"] = (
        company_summary["faturamento"]
        .apply(format_currency)
    )

    print(
        company_summary.to_string(
            index=False
        )
    )

    print()
    print("=" * 90)
    print("VERIFICAÇÃO DOS MESES CONHECIDOS")
    print("=" * 90)

    known_values = {
        "2025-07": 1325529.24,
        "2025-08": 1400742.05,
        "2025-09": 1386129.28,
        "2025-10": 1181446.59,
        "2025-11": 1570324.43,
        "2025-12": 1056109.76,
    }

    for year_month, expected_value in (
        known_values.items()
    ):
        result = monthly[
            monthly["ano_mes"] == year_month
        ]

        if result.empty:
            print(
                f"{year_month}: ERRO "
                "| mês não encontrado"
            )
            continue

        actual_value = float(
            result["faturamento"].iloc[0]
        )

        difference = (
            actual_value - expected_value
        )

        print(
            f"{year_month}: "
            f"{validation_status(difference)} "
            f"| calculado "
            f"{format_currency(actual_value)} "
            f"| esperado "
            f"{format_currency(expected_value)} "
            f"| diferença R$ "
            f"{difference:.4f}"
        )

    print()
    print("=" * 90)
    print("PENDÊNCIA HISTÓRICA CONHECIDA")
    print("=" * 90)

    print(
        "Janeiro a junho de 2025 possuem divergência "
        "em relação à plataforma de referência."
    )
    print(
        "Esses valores não foram corrigidos manualmente "
        "e deverão ser auditados posteriormente."
    )

    print()
    print("=" * 90)
    print("QUANTIDADE DE LINHAS")
    print("=" * 90)

    print(
        f"Histórico mensal:     {len(monthly):,}"
    )
    print(
        f"Histórico anual:      {len(yearly):,}"
    )
    print(
        "Empresa por mês:      "
        f"{len(company_monthly):,}"
    )
    print(
        "Vendedor por empresa: "
        f"{len(seller_monthly):,}"
    )

    print()
    print("=" * 90)
    print("VALIDAÇÃO FINALIZADA")
    print("=" * 90)


if __name__ == "__main__":
    main()