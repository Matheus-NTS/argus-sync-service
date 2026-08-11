from datetime import datetime

from extractors.pedido_extractor import PedidoExtractor
from extractors.meta_extractor import MetaExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.period_transformer import PeriodTransformer
from services.goal_metrics import GoalMetrics
from features.executive_dashboard.executive_dashboard import ExecutiveDashboard
from features.insights.executive_insights import ExecutiveInsights
from features.argus_ai.argus_ai_engine import ArgusAiEngine


class ExecutivePipeline:
    LEGACY_PERIOD = "current_month"
    AI_PERIODS = ("current_month", "last_30_days", "ytd")

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):
        hoje = datetime.today()
        reference_date = hoje.date().isoformat()

        legacy_dashboard_data = self._legacy_dashboard_data(hoje)
        legacy_snapshot = self._legacy_snapshot(
            reference_date,
            legacy_dashboard_data,
        )

        self.supabase.upsert(
            "executive_dashboard_snapshot",
            legacy_snapshot,
            "reference_date,period_type",
        )

        legacy_count = self._legacy_insights(
            reference_date,
            legacy_dashboard_data,
        )

        totals = {
            "briefing": 0,
            "changes": 0,
            "attention": 0,
            "opportunities": 0,
            "actions": 0,
            "events": 0,
        }

        engine = ArgusAiEngine()

        for period_type in self.AI_PERIODS:
            executive_snapshot = (
                legacy_snapshot
                if period_type == self.LEGACY_PERIOD
                else self._period_snapshot(
                    reference_date,
                    period_type,
                )
            )

            self.supabase.upsert(
                "executive_dashboard_snapshot",
                executive_snapshot,
                "reference_date,period_type",
            )

            result = engine.build(
                reference_date=reference_date,
                period_type=period_type,
                executive_snapshot=executive_snapshot,
                previous_snapshot=self._previous_snapshot(
                    reference_date,
                    period_type,
                ),
                **self._sources(
                    reference_date,
                    period_type,
                ),
            )

            self._publish(
                reference_date,
                period_type,
                result,
            )

            totals["briefing"] += 1
            totals["changes"] += len(result["changes"])
            totals["attention"] += len(result["attention"])
            totals["opportunities"] += len(result["opportunities"])
            totals["actions"] += len(result["actions"])
            totals["events"] += len(result["events"])

        return {
            "executive_snapshot": legacy_snapshot,
            "insights_count": legacy_count,
            "argus_ai_periods": len(self.AI_PERIODS),
            "argus_ai_briefing": totals["briefing"],
            "argus_ai_changes": totals["changes"],
            "argus_ai_attention": totals["attention"],
            "argus_ai_opportunities": totals["opportunities"],
            "argus_ai_actions": totals["actions"],
            "argus_ai_events": totals["events"],
        }

    def _legacy_dashboard_data(self, hoje):
        pedidos = PedidoExtractor(self.sql_connector).extract()
        metas = MetaExtractor(self.sql_connector).extract()
        pedidos = PedidoTransformer().filter_revenue_orders(
            pedidos
        )

        pedidos_mes = PeriodTransformer().filter_by_month(
            pedidos,
            "Data",
            hoje.month,
            hoje.year,
        )

        metas_mes = metas[
            (metas["mes"] == hoje.month) &
            (metas["ano"] == hoje.year)
        ].copy()

        metas_mes = GoalMetrics().add_goal_levels(
            metas_mes
        )

        return ExecutiveDashboard().build(
            pedidos_mes,
            metas_mes,
        )

    def _legacy_snapshot(
        self,
        reference_date,
        dashboard_data,
    ):
        return {
            "reference_date": reference_date,
            "period_type": self.LEGACY_PERIOD,
            "faturamento_total": round(
                float(dashboard_data["faturamento_total"]),
                2,
            ),
            "pedidos": int(dashboard_data["pedidos"]),
            "itens_vendidos": int(
                dashboard_data["itens_vendidos"]
            ),
            "clientes": int(dashboard_data["clientes"]),
            "ticket_medio": round(
                float(dashboard_data["ticket_medio"]),
                2,
            ),
            "meta_base": round(
                float(dashboard_data["meta_base"]),
                2,
            ),
            "super_meta": round(
                float(dashboard_data["super_meta"]),
                2,
            ),
            "hiper_meta": round(
                float(dashboard_data["hiper_meta"]),
                2,
            ),
            "atingimento_meta_base": round(
                float(
                    dashboard_data[
                        "atingimento_meta_base"
                    ]
                ),
                4,
            ),
            "atingimento_super_meta": round(
                float(
                    dashboard_data[
                        "atingimento_super_meta"
                    ]
                ),
                4,
            ),
            "atingimento_hiper_meta": round(
                float(
                    dashboard_data[
                        "atingimento_hiper_meta"
                    ]
                ),
                4,
            ),
        }

    def _period_snapshot(
        self,
        reference_date,
        period_type,
    ):
        rows = self._many(
            "mart_sales_company_snapshot",
            reference_date,
            period_type,
            limit=100,
        )

        faturamento = sum(
            float(row.get("faturamento_total") or 0)
            for row in rows
        )
        pedidos = sum(
            int(row.get("pedidos") or 0)
            for row in rows
        )
        itens = sum(
            int(row.get("itens_vendidos") or 0)
            for row in rows
        )
        clientes = sum(
            int(row.get("clientes") or 0)
            for row in rows
        )

        return {
            "reference_date": reference_date,
            "period_type": period_type,
            "faturamento_total": round(
                faturamento,
                2,
            ),
            "pedidos": pedidos,
            "itens_vendidos": itens,
            "clientes": clientes,
            "ticket_medio": round(
                faturamento / pedidos
                if pedidos > 0
                else 0,
                2,
            ),
            "meta_base": 0,
            "super_meta": 0,
            "hiper_meta": 0,
            "atingimento_meta_base": 0,
            "atingimento_super_meta": 0,
            "atingimento_hiper_meta": 0,
        }

    def _legacy_insights(
        self,
        reference_date,
        dashboard_data,
    ):
        filters = {
            "reference_date": reference_date,
            "period_type": self.LEGACY_PERIOD,
        }

        self.supabase.delete_where(
            "mart_executive_insights",
            filters,
        )

        rows = ExecutiveInsights().build(
            dashboard_data,
            None,
        )

        records = [
            {
                **filters,
                "insight_type": row["insight_type"],
                "severity": row["severity"],
                "title": row["title"],
                "description": row["description"],
            }
            for row in rows
        ]

        if records:
            self.supabase.insert(
                "mart_executive_insights",
                records,
            )

        return len(records)

    def _previous_snapshot(
        self,
        reference_date,
        period_type,
    ):
        rows = self.supabase.select_rows(
            "executive_dashboard_snapshot",
            filters={"period_type": period_type},
            lt_filters={
                "reference_date": reference_date
            },
            order_by="reference_date",
            descending=True,
            limit=1,
        )

        return rows[0] if rows else None

    def _one(
        self,
        table,
        reference_date,
        period_type,
    ):
        rows = self._many(
            table,
            reference_date,
            period_type,
            limit=1,
        )

        return rows[0] if rows else None

    def _many(
        self,
        table,
        reference_date,
        period_type,
        order_by=None,
        limit=500,
    ):
        return self.supabase.select_rows(
            table,
            filters={
                "reference_date": reference_date,
                "period_type": period_type,
            },
            order_by=order_by,
            limit=limit,
        )

    def _sources(
        self,
        reference_date,
        period_type,
    ):
        return {
            "commercial": self._one(
                "mart_commercial_overview",
                reference_date,
                period_type,
            ),
            "stock": self._one(
                "mart_stock_overview",
                reference_date,
                "current",
            ),
            "customers": self._one(
                "mart_customer_overview",
                reference_date,
                period_type,
            ),
            "products": self._one(
                "mart_product_overview",
                reference_date,
                period_type,
            ),
            "profitability": self._one(
                "mart_profitability_overview",
                reference_date,
                period_type,
            ),
            "sellers": self._many(
                "mart_commercial_seller_snapshot",
                reference_date,
                period_type,
                "arena_position",
            ),
            "commercial_alerts": self._many(
                "mart_commercial_alerts",
                reference_date,
                period_type,
            ),
            "commercial_recommendations": self._many(
                "mart_commercial_recommendations",
                reference_date,
                period_type,
            ),
            "customer_risks": self._many(
                "mart_commercial_customer_risk",
                reference_date,
                period_type,
            ),
            "product_risks": self._many(
                "mart_commercial_product_risk",
                reference_date,
                period_type,
            ),
            "stock_risks": self._many(
                "mart_stock_risk",
                reference_date,
                "current",
            ),
            "profitability_risks": self._many(
                "mart_profitability_risk",
                reference_date,
                period_type,
            ),
            "profitability_recommendations": self._many(
                "mart_profitability_recommendation",
                reference_date,
                period_type,
            ),
            "lost_sales": self.supabase.select_rows(
                "mart_lost_sales_snapshot",
                filters={
                    "reference_date": reference_date
                },
                limit=1000,
            ),
        }

    def _publish(
        self,
        reference_date,
        period_type,
        result,
    ):
        filters = {
            "reference_date": reference_date,
            "period_type": period_type,
        }

        self.supabase.replace_snapshot(
            "mart_argus_ai_briefing",
            filters,
            result["briefing"],
        )
        self.supabase.replace_snapshot(
            "mart_argus_ai_changes",
            filters,
            result["changes"],
        )
        self.supabase.replace_snapshot(
            "mart_argus_ai_attention",
            filters,
            result["attention"],
        )
        self.supabase.replace_snapshot(
            "mart_argus_ai_opportunities",
            filters,
            result["opportunities"],
        )
        self.supabase.replace_snapshot(
            "mart_argus_ai_actions",
            filters,
            result["actions"],
        )

        self.supabase.delete_where(
            "mart_argus_ai_events",
            filters,
        )

        if result["events"]:
            self.supabase.insert(
                "mart_argus_ai_events",
                result["events"],
            )
