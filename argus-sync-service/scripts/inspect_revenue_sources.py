import pandas as pd

from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor
from extractors.meta_extractor import MetaExtractor


def print_section(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def main():
    connector = SQLServerConnector()

    print_section("EXTRAÇÃO DE PEDIDOS")

    pedidos = PedidoExtractor(
        connector
    ).extract()

    print(
        f"Linhas: {len(pedidos):,}"
    )

    print()
    print("Colunas:")
    for column in pedidos.columns:
        print(f"  - {column}")

    print()
    print("Tipos:")
    print(
        pedidos.dtypes.to_string()
    )

    print()
    print("Primeiros registros:")
    print(
        pedidos.head(3).to_string(
            index=False
        )
    )

    print_section("EXTRAÇÃO DE METAS")

    metas = MetaExtractor(
        connector
    ).extract()

    print(
        f"Linhas: {len(metas):,}"
    )

    print()
    print("Colunas:")
    for column in metas.columns:
        print(f"  - {column}")

    print()
    print("Tipos:")
    print(
        metas.dtypes.to_string()
    )

    print()
    print("Primeiros registros:")
    print(
        metas.head(10).to_string(
            index=False
        )
    )

    print_section("VALORES DISTINTOS DAS METAS")

    for column in metas.columns:
        unique_count = metas[
            column
        ].nunique(
            dropna=False
        )

        print()
        print(
            f"{column} "
            f"({unique_count:,} valores distintos)"
        )

        if unique_count <= 30:
            values = (
                metas[column]
                .drop_duplicates()
                .head(30)
                .tolist()
            )

            for value in values:
                print(
                    f"  - {value}"
                )

    print_section("VALIDAÇÃO FINALIZADA")


if __name__ == "__main__":
    main()