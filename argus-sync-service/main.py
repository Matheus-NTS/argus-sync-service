from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor


def main():

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    connector = SQLServerConnector()

    extractor = PedidoExtractor(connector)

    pedidos = extractor.extract()

    print()

    print(f"Pedidos carregados: {len(pedidos):,}")

    print()

    print(pedidos.head())


if __name__ == "__main__":
    main()