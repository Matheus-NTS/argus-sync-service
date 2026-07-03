from datetime import datetime

from config.periods import MVP_PERIODS, resolve_window

from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer

from pipelines.sales_mart_pipeline import SalesMartPipeline
from pipelines.commercial_intelligence_pipeline import CommercialIntelligencePipeline


class SalesPipeline:

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):

        hoje = datetime.today().date()

        pedido_extractor = PedidoExtractor(self.sql_connector)
        pedidos = pedido_extractor.extract()

        pedido_transformer = PedidoTransformer()
        pedidos = pedido_transformer.filter_revenue_orders(pedidos)

        pedidos["Data"] = __import__("pandas").to_datetime(
            pedidos["Data"],
            errors="coerce"
        )

        sales_marts = SalesMartPipeline(self.supabase)

        current_month_result = None
        period_results = {}

        for period_type in MVP_PERIODS:

            window = resolve_window(period_type, hoje)

            pedidos_periodo = pedidos[
                (pedidos["Data"].dt.date >= window.date_from) &
                (pedidos["Data"].dt.date <= window.date_to)
            ].copy()

            print(
                f"  Gerando marts de vendas: {period_type} "
                f"({window.date_from} até {window.date_to}) "
                f"- {len(pedidos_periodo)} registros"
            )

            mart_result = sales_marts.run(
                pedidos_periodo,
                period_type=period_type
            )

            period_results[period_type] = {
                "seller_ranking": len(mart_result["seller_df"]),
                "companies": len(mart_result["company_df"]),
                "products": len(mart_result["product_df"]),
                "customers": len(mart_result["customer_df"]),
                "categories": len(mart_result["category_df"])
            }

            if period_type == "current_month":
                current_month_result = mart_result

        if current_month_result is None:
            raise RuntimeError("current_month não foi gerado.")

        intelligence = CommercialIntelligencePipeline(self.supabase)
        intelligence_result = intelligence.run(
            current_month_result["seller_df"],
            current_month_result["company_df"],
            current_month_result["product_df"],
            current_month_result["customer_df"],
            current_month_result["category_df"]
        )

        return {
            "seller_ranking": len(current_month_result["seller_df"]),
            "companies": len(current_month_result["company_df"]),
            "products": len(current_month_result["product_df"]),
            "customers": len(current_month_result["customer_df"]),
            "categories": len(current_month_result["category_df"]),
            "periods_generated": len(period_results),
            **intelligence_result
        }