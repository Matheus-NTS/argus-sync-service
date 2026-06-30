from datetime import datetime

from connectors.sql_server import SQLServerConnector
from connectors.supabase_connector import SupabaseConnector
from extractors.pedido_extractor import PedidoExtractor
from extractors.meta_extractor import MetaExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.period_transformer import PeriodTransformer
from services.goal_metrics import GoalMetrics
from features.executive_dashboard.executive_dashboard import ExecutiveDashboard
from features.sales.seller_ranking import SellerRanking


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

    pedidos_mes = period_transformer.filter_by_month(
        pedidos, "Data", hoje.month, hoje.year
    )

    metas_mes = metas[
        (metas["mes"] == hoje.month) &
        (metas["ano"] == hoje.year)
    ]

    goal_metrics = GoalMetrics()
    metas_mes = goal_metrics.add_goal_levels(metas_mes)

    dashboard = ExecutiveDashboard()
    dashboard_data = dashboard.build(pedidos_mes, metas_mes)

    executive_snapshot = {
        "reference_date": hoje.date().isoformat(),
        "period_type": "current_month",
        "faturamento_total": round(float(dashboard_data["faturamento_total"]), 2),
        "pedidos": int(dashboard_data["pedidos"]),
        "itens_vendidos": int(dashboard_data["itens_vendidos"]),
        "clientes": int(dashboard_data["clientes"]),
        "ticket_medio": round(float(dashboard_data["ticket_medio"]), 2),
        "meta_base": round(float(dashboard_data["meta_base"]), 2),
        "super_meta": round(float(dashboard_data["super_meta"]), 2),
        "hiper_meta": round(float(dashboard_data["hiper_meta"]), 2),
        "atingimento_meta_base": round(float(dashboard_data["atingimento_meta_base"]), 4),
        "atingimento_super_meta": round(float(dashboard_data["atingimento_super_meta"]), 4),
        "atingimento_hiper_meta": round(float(dashboard_data["atingimento_hiper_meta"]), 4),
    }

    supabase.insert("executive_dashboard_snapshot", executive_snapshot)

    seller_ranking = SellerRanking()
    ranking_df = seller_ranking.build(pedidos_mes)

    ranking_records = []

    for _, row in ranking_df.iterrows():
        ranking_records.append({
            "reference_date": hoje.date().isoformat(),
            "period_type": "current_month",
            "vendedor": row["Vendedor"],
            "empresa": row["Empresa"],
            "faturamento_total": round(float(row["faturamento_total"]), 2),
            "pedidos": int(row["pedidos"]),
            "itens_vendidos": int(row["itens_vendidos"]),
            "clientes": int(row["clientes"]),
            "ticket_medio": round(float(row["ticket_medio"]), 2),
        })

    if ranking_records:
        supabase.insert("sales_seller_ranking_snapshot", ranking_records)

    print("Snapshot executivo gravado no Supabase.")
    print(f"Ranking de vendedores gravado: {len(ranking_records)} vendedores.")
    print(ranking_df.head(10))


if __name__ == "__main__":
    main()