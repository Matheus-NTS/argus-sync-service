from datetime import date

from connectors.sql_server import SQLServerConnector
from extractors.meta_extractor import MetaExtractor
from features.intelligence.revenue.meta_dataset import (
    MetaDataset,
)


def print_section(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def main():
    connector = SQLServerConnector()

    metas_raw = MetaExtractor(
        connector
    ).extract()

    dataset = MetaDataset(
        reference_date=date.today(),
    ).build(
        metas_raw
    )

    print_section("META POR VENDEDOR")

    print(
        dataset.seller_monthly[
            [
                "ano",
                "mes",
                "empresa",
                "vendedor",
                "vendedor_key",
                "meta",
                "status_meta",
            ]
        ].to_string(
            index=False
        )
    )

    print_section("META POR EMPRESA")

    print(
        dataset.company_monthly[
            [
                "ano",
                "mes",
                "empresa",
                "meta",
                "vendedores",
                "vendedores_com_meta",
                "vendedores_pendentes",
                "status_meta",
            ]
        ].to_string(
            index=False
        )
    )

    print_section("META GERAL")

    print(
        dataset.general_monthly[
            [
                "ano",
                "mes",
                "empresa",
                "meta",
                "empresas",
                "vendedores",
                "vendedores_com_meta",
                "vendedores_pendentes",
                "status_meta",
            ]
        ].to_string(
            index=False
        )
    )

    print_section("VALIDAÇÕES")

    seller_total = (
        dataset.seller_monthly
        .groupby(
            [
                "ano",
                "mes",
            ]
        )["meta"]
        .sum()
        .sort_index()
    )

    general_total = (
        dataset.general_monthly
        .set_index(
            [
                "ano",
                "mes",
            ]
        )["meta"]
        .sort_index()
    )

    difference = (
        seller_total
        - general_total
    ).abs()

    print(
        "Maior diferença entre soma dos vendedores "
        "e meta geral:"
    )
    print(
        float(
            difference.max()
            if not difference.empty
            else 0
        )
    )

    duplicates = (
        dataset.seller_monthly
        .duplicated(
            subset=[
                "empresa",
                "vendedor_key",
                "ano",
                "mes",
            ]
        )
        .sum()
    )

    print(
        f"Duplicidades: {int(duplicates):,}"
    )

    future_zero = (
        dataset.seller_monthly[
            (
                dataset.seller_monthly[
                    "period_start"
                ]
                > dataset.seller_monthly[
                    "reference_date"
                ]
                .dt.to_period("M")
                .dt.to_timestamp()
            )
            & (
                dataset.seller_monthly[
                    "meta"
                ] == 0
            )
        ]
    )

    invalid_future_status = future_zero[
        future_zero["status_meta"]
        != "pending"
    ]

    print(
        "Metas futuras zeradas não classificadas "
        f"como pending: {len(invalid_future_status):,}"
    )

    print_section("VALIDAÇÃO FINALIZADA")


if __name__ == "__main__":
    main()