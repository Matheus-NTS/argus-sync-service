from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor
from extractors.meta_extractor import MetaExtractor
from transformers.pedido_transformer import PedidoTransformer
from features.executive_dashboard.executive_dashboard import ExecutiveDashboard


def main():

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    connector = SQLServerConnector()

    pedido_extractor = PedidoExtractor(connector)
    meta_extractor = MetaExtractor(connector)

    pedidos = pedido_extractor.extract()
    metas = meta_extractor.extract()

    transformer = PedidoTransformer()
    pedidos_faturamento = transformer.filter_revenue_orders(pedidos)

    dashboard = ExecutiveDashboard()
    dados = dashboard.build(pedidos_faturamento)

    print()
    print(f"Pedidos extraídos: {len(pedidos):,}")
    print(f"Pedidos válidos para faturamento: {len(pedidos_faturamento):,}")
    print(f"Metas carregadas: {len(metas):,}")

    print()
    print("=" * 60)
    print("EXECUTIVE DASHBOARD")
    print("=" * 60)

    print(f"Faturamento Total : R$ {dados['faturamento_total']:,.2f}")
    print(f"Pedidos           : {dados['pedidos']:,}")
    print(f"Clientes          : {dados['clientes']:,}")
    print(f"Ticket Médio      : R$ {dados['ticket_medio']:,.2f}")

    print()
    print("=" * 60)
    print("AMOSTRA DE METAS")
    print("=" * 60)
    print(metas.head())


if __name__ == "__main__":
    main()