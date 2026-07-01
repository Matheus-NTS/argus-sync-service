from datetime import datetime

from features.sales.seller_ranking import SellerRanking
from features.sales.company_performance import CompanyPerformance
from features.sales.product_performance import ProductPerformance
from features.sales.customer_performance import CustomerPerformance
from features.sales.category_performance import CategoryPerformance


class SalesMartPipeline:

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

    def run(self, pedidos_mes):

        hoje = datetime.today()

        seller_df = SellerRanking().build(pedidos_mes)
        company_df = CompanyPerformance().build(pedidos_mes)
        product_df = ProductPerformance().build(pedidos_mes)
        customer_df = CustomerPerformance().build(pedidos_mes)
        category_df = CategoryPerformance().build(pedidos_mes)

        # Nesta primeira versão ainda NÃO movemos os replace_snapshot.
        # O objetivo desta Sprint é separar a geração dos DataFrames
        # da orquestração principal.

        return {
            "seller_df": seller_df,
            "company_df": company_df,
            "product_df": product_df,
            "customer_df": customer_df,
            "category_df": category_df
        }