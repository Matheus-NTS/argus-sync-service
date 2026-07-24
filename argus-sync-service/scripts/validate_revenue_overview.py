from datetime import date

from connectors.sql_server import SQLServerConnector
from extractors.meta_extractor import MetaExtractor
from extractors.pedido_extractor import PedidoExtractor
from features.intelligence.revenue.meta_dataset import (
    MetaDataset,
)
from features.intelligence.revenue.revenue_dataset import (
    RevenueDataset,
)
from features.intelligence.revenue.revenue_history import (
    RevenueHistory,
)
from features.intelligence.revenue.revenue_overview import (
    RevenueOverview,
)


def print_section(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def main():
    connector = SQLServerConnector()

    pedidos_raw = PedidoExtractor(
        connector
    ).extract()

    metas_raw = MetaExtractor(
        connector
    ).extract()

    revenue = RevenueDataset().build(
        pedidos_raw
    )

    history = RevenueHistory().build(
        revenue
    )

    metas = MetaDataset(
        reference_date=date.today(),
    ).build(
        metas_raw
    )

    overview = RevenueOverview(
        reference_date=date.today(),
    ).build(
        history=history,
        metas=metas,
    )

    print_section("OVERVIEW MENSAL")

    print(
        overview.monthly[
            [
                "ano",
                "mes",
                "faturamento",
                "meta",
                "supermeta",
                "hipermeta",
                "atingimento_meta",
                "gap_meta",
                "status_meta",
                "faixa_desempenho",
            ]
        ].tail(24).to_string(
            index=False
        )
    )

    print_section("OVERVIEW POR EMPRESA — PERÍODO ATUAL")

    current_year = date.today().year
    current_month = date.today().month

    current_companies = overview.company_monthly[
        (
            overview.company_monthly["ano"]
            == current_year
        )
        & (
            overview.company_monthly["mes"]
            == current_month
        )
    ]

    print(
        current_companies[
            [
                "empresa",
                "faturamento",
                "meta",
                "atingimento_meta",
                "gap_meta",
                "status_meta",
                "faixa_desempenho",
            ]
        ].to_string(
            index=False
        )
    )

    print_section("OVERVIEW POR VENDEDOR — PERÍODO ATUAL")

    current_sellers = overview.seller_monthly[
        (
            overview.seller_monthly["ano"]
            == current_year
        )
        & (
            overview.seller_monthly["mes"]
            == current_month
        )
    ].sort_values(
        [
            "empresa",
            "faturamento",
        ],
        ascending=[
            True,
            False,
        ],
    )

    print(
        current_sellers[
            [
                "empresa",
                "vendedor",
                "vendedor_key",
                "faturamento",
                "meta",
                "atingimento_meta",
                "gap_meta",
                "status_meta",
                "faixa_desempenho",
            ]
        ].to_string(
            index=False
        )
    )

    print_section("RESUMO ATUAL")

    print(
        overview.current_summary.to_string(
            index=False
        )
    )

    print_section("RECONCILIAÇÃO")

    history_total = (
        history["monthly"]["faturamento"]
        .sum()
    )

    overview_total = (
        overview.monthly["faturamento"]
        .sum()
    )

    print(
        "Diferença entre histórico e overview: "
        f"{abs(history_total - overview_total):.6f}"
    )

    seller_revenue = (
        overview.seller_monthly
        .groupby(
            [
                "ano",
                "mes",
            ]
        )["faturamento"]
        .sum()
        .sort_index()
    )

    consolidated_revenue = (
        overview.monthly
        .set_index(
            [
                "ano",
                "mes",
            ]
        )["faturamento"]
        .sort_index()
    )

    revenue_difference = (
        seller_revenue
        - consolidated_revenue
    ).abs()

    print(
        "Maior diferença mensal entre vendedores "
        "e consolidado: "
        f"{revenue_difference.max():.6f}"
    )

    valid_targets = overview.monthly[
        overview.monthly["meta_valida"]
    ]

    invalid_attainment = valid_targets[
        valid_targets["atingimento_meta"].isna()
    ]

    print(
        "Metas válidas sem atingimento calculado: "
        f"{len(invalid_attainment):,}"
    )

    pending_with_attainment = overview.monthly[
        (
            overview.monthly["status_meta"]
            == "pending"
        )
        & (
            overview.monthly[
                "atingimento_meta"
            ].notna()
        )
    ]

    print(
        "Metas pendentes com atingimento indevido: "
        f"{len(pending_with_attainment):,}"
    )

    print_section("VALIDAÇÃO FINALIZADA")


if __name__ == "__main__":
    main()