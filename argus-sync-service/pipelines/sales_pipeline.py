from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.period_transformer import PeriodTransformer

from pipelines.sales_mart_pipeline import SalesMartPipeline
from pipelines.commercial_intelligence_pipeline import CommercialIntelligencePipeline


class SalesPipeline:

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):

        pedido_extractor = PedidoExtractor(self.sql_connector)
        pedidos = pedido_extractor.extract()

        pedido_transformer = PedidoTransformer()
        pedidos = pedido_transformer.filter_revenue_orders(pedidos)

        period_transformer = PeriodTransformer()
        hoje = __import__("datetime").datetime.today()

        pedidos_mes = period_transformer.filter_by_month(
            pedidos,
            "Data",
            hoje.month,
            hoje.year
        )

        sales_marts = SalesMartPipeline(self.supabase)
        mart_result = sales_marts.run(pedidos_mes)

        intelligence = CommercialIntelligencePipeline(self.supabase)
        intelligence_result = intelligence.run(
            mart_result["seller_df"],
            mart_result["company_df"],
            mart_result["product_df"],
            mart_result["customer_df"],
            mart_result["category_df"]
        )

        return {
            "seller_ranking": len(mart_result["seller_df"]),
            "companies": len(mart_result["company_df"]),
            "products": len(mart_result["product_df"]),
            "customers": len(mart_result["customer_df"]),
            "categories": len(mart_result["category_df"]),
            **intelligence_result
        }