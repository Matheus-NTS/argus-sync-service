from datetime import datetime

from connectors.sql_server import SQLServerConnector
from connectors.supabase_connector import SupabaseConnector
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
    supabase = SupabaseConnector()

    pedido_extractor = PedidoExtractor(connector)
    meta_extractor = MetaExtractor(connector)

    pedidos = pedido_extractor.extract()
    metas = meta_extractor.extract()

    pedido_transformer = PedidoTransformer()
    period_transformer = PeriodTransformer()

    pedidos = pedido_transformer.filter_revenue_orders(pedidos)

    hoje = datetime.today()

    pedidos_mes = period_transformer.filter_by_month(pedidos, "Data", hoje.month, hoje.year)
    metas_mes = metas[(metas["mes"] == hoje.month) & (metas["ano"] == hoje.year)]

    goal_metrics = GoalMetrics()
    metas_mes = goal_metrics.add_goal_levels(metas_mes)

    dashboard = ExecutiveDashboard()
    dados = dashboard.build(pedidos_mes, metas_mes)

    snapshot = {
        "reference_date": hoje.date().isoformat(),
        "period_type": "current_month",
        "faturamento_total": round(float(dados["faturamento_total"]), 2),
        "pedidos": int(dados["pedidos"]),
        "itens_vendidos": int(dados["itens_vendidos"]),
        "clientes": int(dados["clientes"]),
        "ticket_medio": round(float(dados["ticket_medio"]), 2),
        "meta_base": round(float(dados["meta_base"]), 2),
        "super_meta": round(float(dados["super_meta"]), 2),
        "hiper_meta": round(float(dados["hiper_meta"]), 2),
        "atingimento_meta_base": round(float(dados["atingimento_meta_base"]), 4),
        "atingimento_super_meta": round(float(dados["atingimento_super_meta"]), 4),
        "atingimento_hiper_meta": round(float(dados["atingimento_hiper_meta"]), 4),
    }

    supabase.insert("executive_dashboard_snapshot", snapshot)

    print("Snapshot gravado no Supabase com sucesso!")
    print(snapshot)


if __name__ == "__main__":
    main()