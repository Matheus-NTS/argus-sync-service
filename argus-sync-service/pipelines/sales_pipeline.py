from datetime import datetime

from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.period_transformer import PeriodTransformer

from features.sales.seller_ranking import SellerRanking
from features.sales.company_performance import CompanyPerformance


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

        # ==========================
        # Ranking de vendedores
        # ==========================

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

        self.supabase.upsert(
            "sales_seller_ranking_snapshot",
            ranking_records,
            "reference_date,period_type,vendedor"
        )

        # ==========================
        # Performance por empresa
        # ==========================

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

        self.supabase.upsert(
            "mart_sales_company_snapshot",
            company_records,
            "reference_date,period_type,empresa"
        )

        return {
            "seller_ranking": len(ranking_records),
            "companies": len(company_records)
        }