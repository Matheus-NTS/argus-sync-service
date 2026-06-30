from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer
from features.executive_dashboard.executive_dashboard import ExecutiveDashboard


def main():

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    # Conexão com o banco
    connector = SQLServerConnector()

    # Extração dos pedidos
    extractor = PedidoExtractor(connector)
    pedidos = extractor.extract()

    # Aplicação das regras de negócio
    transformer = PedidoTransformer()
    pedidos_faturamento = transformer.filter_revenue_orders(pedidos)

    # Dashboard Executivo
    dashboard = ExecutiveDashboard()
    dados = dashboard.build(pedidos_faturamento)

    # Informações gerais
    print()
    print(f"Pedidos extraídos: {len(pedidos):,}")
    print(f"Pedidos válidos para faturamento: {len(pedidos_faturamento):,}")

    print()
    print("=" * 60)
    print("EXECUTIVE DASHBOARD")
    print("=" * 60)

    print(f"Faturamento Total : R$ {dados['faturamento_total']:,.2f}")
    print(f"Pedidos           : {dados['pedidos']:,}")
    print(f"Clientes          : {dados['clientes']:,}")
    print(f"Ticket Médio      : R$ {dados['ticket_medio']:,.2f}")


if __name__ == "__main__":
    main()