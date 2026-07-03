from datetime import datetime

import pandas as pd

from features.sales.seller_ranking import SellerRanking
from features.sales.company_performance import CompanyPerformance
from features.sales.product_performance import ProductPerformance
from features.sales.customer_performance import CustomerPerformance
from features.sales.category_performance import CategoryPerformance


class SalesMartPipeline:

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

    def run(self, pedidos, period_type="current_month"):

        hoje = datetime.today()

        filters = {
            "reference_date": hoje.date().isoformat(),
            "period_type": period_type
        }

        seller_df = SellerRanking().build(pedidos)
        company_df = CompanyPerformance().build(pedidos)
        product_df = ProductPerformance().build(pedidos)
        customer_df = CustomerPerformance().build(pedidos)
        category_df = CategoryPerformance().build(pedidos)

        self._save_sellers(seller_df, filters)
        self._save_companies(company_df, filters)
        self._save_products(product_df, filters)
        self._save_customers(customer_df, filters)
        self._save_categories(category_df, filters)

        return {
            "seller_df": seller_df,
            "company_df": company_df,
            "product_df": product_df,
            "customer_df": customer_df,
            "category_df": category_df
        }

    def _save_sellers(self, seller_df, filters):

        seller_records = []

        for _, row in seller_df.iterrows():
            seller_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "vendedor": row["Vendedor"],
                "empresa": "TOTAL",
                "empresa_breakdown": row["empresa_breakdown"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot(
            "sales_seller_ranking_snapshot",
            filters,
            seller_records
        )

    def _save_companies(self, company_df, filters):

        company_records = []

        for _, row in company_df.iterrows():
            company_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot(
            "mart_sales_company_snapshot",
            filters,
            company_records
        )

    def _save_products(self, product_df, filters):

        product_records = []

        for _, row in product_df.iterrows():
            product_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "prod_codigo": row["prod_codigo"],
                "produto": row["produto"],
                "classificacao": row["Classificacao"],
                "unidade": row["unidade"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "quantidade": float(row["quantidade"]),
                "pedidos": int(row["pedidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot(
            "mart_sales_product_snapshot",
            filters,
            product_records
        )

    def _save_customers(self, customer_df, filters):

        customer_records = []

        for _, row in customer_df.iterrows():

            ultima_compra = None

            if pd.notnull(row["ultima_compra"]):
                try:
                    ultima_compra = pd.to_datetime(row["ultima_compra"]).date().isoformat()
                except Exception:
                    ultima_compra = None

            customer_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "codigo_cliente": str(row["codigo_cliente"]),
                "cliente": row["Cliente"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "mix_produtos": int(row["mix_produtos"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2),
                "ultima_compra": ultima_compra
            })

        self.supabase.replace_snapshot(
            "mart_sales_customer_snapshot",
            filters,
            customer_records
        )

    def _save_categories(self, category_df, filters):

        category_records = []

        for _, row in category_df.iterrows():
            category_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "categoria": row["Categoria"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "produtos": int(row["produtos"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot(
            "mart_sales_category_snapshot",
            filters,
            category_records
        )