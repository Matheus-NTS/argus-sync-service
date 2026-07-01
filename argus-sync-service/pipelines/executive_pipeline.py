from datetime import datetime

from extractors.pedido_extractor import PedidoExtractor
from extractors.meta_extractor import MetaExtractor

from transformers.pedido_transformer import PedidoTransformer
from transformers.period_transformer import PeriodTransformer

from services.goal_metrics import GoalMetrics

from features.executive_dashboard.executive_dashboard import ExecutiveDashboard
from features.insights.executive_insights import ExecutiveInsights


class ExecutivePipeline:

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):

        pedido_extractor = PedidoExtractor(self.sql_connector)
        meta_extractor = MetaExtractor(self.sql_connector)

        pedidos = pedido_extractor.extract()
        metas = meta_extractor.extract()

        pedido_transformer = PedidoTransformer()
        period_transformer = PeriodTransformer()

        pedidos = pedido_transformer.filter_revenue_orders(pedidos)

        hoje = datetime.today()

        pedidos_mes = period_transformer.filter_by_month(
            pedidos,
            "Data",
            hoje.month,
            hoje.year
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

        self.supabase.upsert(
            "executive_dashboard_snapshot",
            executive_snapshot,
            "reference_date,period_type"
        )

        self.supabase.delete_where(
            "mart_executive_insights",
            {
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month"
            }
        )

        executive_insights = ExecutiveInsights()
        insights = executive_insights.build(dashboard_data, None)

        insight_records = []

        for insight in insights:
            insight_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
                "insight_type": insight["insight_type"],
                "severity": insight["severity"],
                "title": insight["title"],
                "description": insight["description"]
            })

        self.supabase.insert(
            "mart_executive_insights",
            insight_records
        )

        return {
            "executive_snapshot": executive_snapshot,
            "insights_count": len(insight_records)
        }