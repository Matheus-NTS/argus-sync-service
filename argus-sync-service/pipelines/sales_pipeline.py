from datetime import datetime

from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.period_transformer import PeriodTransformer

from features.sales.seller_ranking import SellerRanking
from features.sales.company_performance import CompanyPerformance
from features.sales.product_performance import ProductPerformance
from features.sales.customer_performance import CustomerPerformance


class SalesPipeline:

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):

        hoje = datetime.today()

        pedido_extractor = PedidoExtractor(self.sql_connector)
        pedidos = pedido_extractor.extract()

        pedido_transformer = PedidoTransformer()
        pedidos = pedido_transformer.filter_revenue_orders(pedidos)

        period_transformer = PeriodTransformer()

        pedidos_mes = period_transformer.filter_by_month(
            pedidos,
            "Data",
            hoje.month,
            hoje.year
        )

        seller_ranking = SellerRanking()
        ranking_df = seller_ranking.build(pedidos_mes)

        ranking_records = []

        for _, row in ranking_df.iterrows():
            ranking_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
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
            {
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month"
            },
            ranking_records
        )

        company = CompanyPerformance()
        company_df = company.build(pedidos_mes)

        company_records = []

        for _, row in company_df.iterrows():
            company_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
                "empresa": row["Empresa"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot(
            "mart_sales_company_snapshot",
            {
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month"
            },
            company_records
        )

        product = ProductPerformance()
        product_df = product.build(pedidos_mes)

        product_records = []

        for _, row in product_df.iterrows():
            product_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
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
            {
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month"
            },
            product_records
        )

        customer = CustomerPerformance()
        customer_df = customer.build(pedidos_mes)

        customer_records = []

        for _, row in customer_df.iterrows():
            customer_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
                "codigo_cliente": str(row["codigo_cliente"]),
                "cliente": row["Cliente"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "mix_produtos": int(row["mix_produtos"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2),
                "ultima_compra": row["ultima_compra"].date().isoformat()
            })

        self.supabase.replace_snapshot(
            "mart_sales_customer_snapshot",
            {
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month"
            },
            customer_records
        )

        return {
            "seller_ranking": len(ranking_records),
            "companies": len(company_records),
            "products": len(product_records),
            "customers": len(customer_records)
        }