from datetime import datetime
import pandas as pd

from config.periods import MVP_PERIODS, resolve_window

from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer
from extractors.meta_extractor import MetaExtractor
from pipelines.sales_mart_pipeline import SalesMartPipeline
from pipelines.commercial_intelligence_pipeline import CommercialIntelligencePipeline
from pipelines.sales_history_pipeline import SalesHistoryPipeline
from pipelines.revenue_intelligence_pipeline import (
    RevenueIntelligencePipeline,
)

class SalesPipeline:

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):

        hoje = datetime.today().date()

        pedidos = PedidoExtractor(self.sql_connector).extract()
        pedidos = PedidoTransformer().filter_revenue_orders(pedidos)

        pedidos["Data"] = pd.to_datetime(pedidos["Data"], errors="coerce")
        pedidos = pedidos[pedidos["Data"].notna()].copy()

        meta_df = MetaExtractor(
            self.sql_connector
        ).extract()

        sales_marts = SalesMartPipeline(self.supabase)
        intelligence = CommercialIntelligencePipeline(self.supabase)
        history_result = SalesHistoryPipeline(self.supabase).run(pedidos)

        revenue_result = RevenueIntelligencePipeline(
            sql_connector=self.sql_connector,
            supabase_connector=self.supabase,
        ).run(
            pedidos=pedidos
        )

        current_month_result = None
        current_month_intelligence = None
        period_results = {}

        periods_to_generate = ["historico"] + list(MVP_PERIODS)

        for period_type in periods_to_generate:

            if period_type == "historico":
                pedidos_periodo = pedidos.copy()
                date_from = pedidos_periodo["Data"].min().date()
                date_to = pedidos_periodo["Data"].max().date()
            else:
                window = resolve_window(period_type, hoje)
                pedidos_periodo = pedidos[
                    (pedidos["Data"].dt.date >= window.date_from) &
                    (pedidos["Data"].dt.date <= window.date_to)
                ].copy()
                date_from = window.date_from
                date_to = window.date_to

            print(
                f"  Gerando marts de vendas: {period_type} "
                f"({date_from} até {date_to}) "
                f"- {len(pedidos_periodo)} registros"
            )

            mart_result = sales_marts.run(
                pedidos_periodo,
                meta_df=meta_df,
                period_type=period_type
            )

            intelligence_result = intelligence.run(
                mart_result["seller_df"],
                mart_result["company_df"],
                mart_result["product_df_all"],
                mart_result["customer_df_all"],
                mart_result["category_df_all"],
                period_type=period_type
            )

            period_results[period_type] = {
                                "commercial_sellers": (
                    mart_result[
                        "commercial_seller_records"
                    ]
                ),
                "seller_ranking": len(mart_result["seller_df"]),
                "companies": len(mart_result["company_df"]),
                "products": len(mart_result["product_df"]),
                "customers": len(mart_result["customer_df"]),
                "categories": len(mart_result["category_df"]),
                **intelligence_result
            }

            if period_type == "current_month":
                current_month_result = mart_result
                current_month_intelligence = intelligence_result

        if current_month_result is None or current_month_intelligence is None:
            raise RuntimeError("current_month não foi gerado.")

        return {
            "seller_ranking": len(current_month_result["seller_df"]),
                        "commercial_sellers": (
                current_month_result[
                    "commercial_seller_records"
                ]
            ),
            "companies": len(current_month_result["company_df"]),
            "products": len(current_month_result["product_df"]),
            "customers": len(current_month_result["customer_df"]),
            "categories": len(current_month_result["category_df"]),
            "periods_generated": len(period_results),
            **history_result,
            **revenue_result,
            **current_month_intelligence
        }