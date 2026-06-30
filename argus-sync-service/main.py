from datetime import datetime

from connectors.sql_server import SQLServerConnector
from extractors.pedido_extractor import PedidoExtractor
from extractors.meta_extractor import MetaExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.period_transformer import PeriodTransformer
from services.goal_metrics import GoalMetrics
from features.executive_dashboard.executive_dashboard import ExecutiveDashboard


def main():

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    connector = SQLServerConnector()

    # Extração
    pedido_extractor = PedidoExtractor(connector)
    meta_extractor = MetaExtractor(connector)

    pedidos = pedido_extractor.extract()
    metas = meta_extractor.extract()

    # Transformações
    pedido_transformer = PedidoTransformer()
    period_transformer = PeriodTransformer()

    pedidos = pedido_transformer.filter_revenue_orders(pedidos)

    hoje = datetime.today()

    pedidos = period_transformer.filter_by_month(
        pedidos,
        "Data",
        hoje.month,
        hoje.year
    )

    metas = metas[
        (metas["mes"] == hoje.month) &
        (metas["ano"] == hoje.year)
    ]

    goal_metrics = GoalMetrics()
    metas = goal_metrics.add_goal_levels(metas)

    dashboard = ExecutiveDashboard()

    dados = dashboard.build(
        pedidos,
        metas
    )

    print()

    print("=" * 60)
    print(f"DASHBOARD EXECUTIVO - {hoje.strftime('%m/%Y')}")
    print("=" * 60)

    print(f"Faturamento : R$ {dados['faturamento_total']:,.2f}")
    print(f"Pedidos     : {dados['pedidos']:,}")
    print(f"Clientes    : {dados['clientes']:,}")
    print(f"Ticket Médio: R$ {dados['ticket_medio']:,.2f}")

    print()

    print(f"Meta Base   : R$ {dados['meta_base']:,.2f}")
    print(f"Super Meta  : R$ {dados['super_meta']:,.2f}")
    print(f"Hiper Meta  : R$ {dados['hiper_meta']:,.2f}")

    print()

    print(f"Atingimento Meta  : {dados['atingimento_meta_base']:.2%}")
    print(f"Ating. Super Meta : {dados['atingimento_super_meta']:.2%}")
    print(f"Ating. Hiper Meta : {dados['atingimento_hiper_meta']:.2%}")


if __name__ == "__main__":
    main()