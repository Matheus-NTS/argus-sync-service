from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer


def main():
    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    connector = SQLServerConnector()
    extractor = PedidoExtractor(connector)
    transformer = PedidoTransformer()

    pedidos = extractor.extract()
    pedidos_faturamento = transformer.filter_revenue_orders(pedidos)

    print(f"Pedidos extraídos: {len(pedidos):,}")
    print(f"Pedidos válidos para faturamento: {len(pedidos_faturamento):,}")

    print(pedidos_faturamento.head())


if __name__ == "__main__":
    main()