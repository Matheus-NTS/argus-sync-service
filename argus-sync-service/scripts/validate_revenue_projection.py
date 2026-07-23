from datetime import datetime

import pandas as pd

from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor

from features.intelligence.revenue.revenue_dataset import (
    RevenueDataset,
)
from features.intelligence.revenue.revenue_projection import (
    RevenueProjection,
)


def format_currency(value) -> str:
    formatted = f"{float(value):,.2f}"

    return (
        "R$ "
        + formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def main():
    print("=" * 80)
    print("VALIDAÇÃO — PROJEÇÃO DE FATURAMENTO")
    print("=" * 80)

    sql_connector = SQLServerConnector()

    pedidos_raw = PedidoExtractor(
        sql_connector
    ).extract()

    revenue_dataset = RevenueDataset()
    pedidos = revenue_dataset.build(
        pedidos_raw
    )

    current_year = datetime.today().year

    available_years = sorted(
        pedidos["ano"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    print()
    print(
        "Anos disponíveis:",
        available_years,
    )

    completed_years = [
        year
        for year in available_years
        if year < current_year
    ]

    if completed_years:
        base_year = max(completed_years)
    else:
        base_year = max(available_years)

    print(
        f"Ano-base selecionado automaticamente: {base_year}"
    )
    print(
        f"Ano projetado: {base_year + 1}"
    )

    projection_service = RevenueProjection()

    monthly_projection = projection_service.build(
        pedidos,
        base_year=base_year,
    )

    annual_summary = (
        projection_service.build_summary(
            monthly_projection
        )
    )

    print()
    print("=" * 80)
    print("FATURAMENTO REALIZADO NO ANO-BASE")
    print("=" * 80)

    base_view = monthly_projection[
        [
            "mes",
            "mes_nome",
            "faturamento_base",
            "participacao_ano_base",
        ]
    ].copy()

    base_view["faturamento_base"] = (
        base_view["faturamento_base"]
        .apply(format_currency)
    )

    base_view["participacao_ano_base"] = (
        base_view["participacao_ano_base"]
        .apply(
            lambda value: f"{value:.2%}"
        )
    )

    print(
        base_view.to_string(
            index=False
        )
    )

    print()
    print("=" * 80)
    print("RESUMO DOS CENÁRIOS")
    print("=" * 80)

    summary_view = annual_summary.copy()

    summary_view["cenario"] = (
        summary_view["cenario_percentual"]
        .apply(
            lambda value: f"+{value:.0%}"
        )
    )

    for column in [
        "faturamento_ano_base",
        "faturamento_projetado",
        "crescimento_valor",
        "media_mensal_projetada",
    ]:
        summary_view[column] = (
            summary_view[column]
            .apply(format_currency)
        )

    print(
        summary_view[
            [
                "cenario",
                "faturamento_ano_base",
                "faturamento_projetado",
                "crescimento_valor",
                "media_mensal_projetada",
            ]
        ].to_string(
            index=False
        )
    )

    print()
    print("=" * 80)
    print("VALIDAÇÕES")
    print("=" * 80)

    annual_base = float(
        monthly_projection[
            "faturamento_base"
        ].sum()
    )

    for _, row in annual_summary.iterrows():
        expected = (
            annual_base
            * (
                1
                + float(
                    row["cenario_percentual"]
                )
            )
        )

        difference = abs(
            expected
            - float(
                row["faturamento_projetado"]
            )
        )

        status = (
            "OK"
            if difference < 0.02
            else "ERRO"
        )

        print(
            f"  Cenário "
            f"+{row['cenario_percentual']:.0%}: "
            f"{status} "
            f"| diferença R$ {difference:.4f}"
        )

    long_format = (
        projection_service.build_long_format(
            monthly_projection
        )
    )

    print()
    print(
        "Linhas da projeção mensal: "
        f"{len(monthly_projection)}"
    )
    print(
        "Linhas no formato longo: "
        f"{len(long_format)}"
    )

    print()
    print("=" * 80)
    print("VALIDAÇÃO FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    main()