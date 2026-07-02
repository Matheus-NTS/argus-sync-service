from datetime import datetime

import pandas as pd

from extractors.produto_extractor import ProdutoExtractor
from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer

from features.intelligence.stock.stock_snapshot import StockSnapshot


class StockPipeline:

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):

        hoje = datetime.today()

        filters = {
            "reference_date": hoje.date().isoformat(),
            "period_type": "current"
        }

        produto_extractor = ProdutoExtractor(self.sql_connector)
        pedido_extractor = PedidoExtractor(self.sql_connector)

        estoque = produto_extractor.extract()
        vendas = pedido_extractor.extract()

        pedido_transformer = PedidoTransformer()
        vendas = pedido_transformer.filter_revenue_orders(vendas)

        stock_snapshot = StockSnapshot()
        stock_df = stock_snapshot.build(estoque, vendas)

        stock_records = []

        for _, row in stock_df.iterrows():

            ultima_venda = None

            if pd.notnull(row.get("ultima_venda")):
                try:
                    ultima_venda = pd.to_datetime(row["ultima_venda"]).date().isoformat()
                except Exception:
                    ultima_venda = None

            cobertura = row.get("cobertura_estoque")
            if pd.isna(cobertura):
                cobertura = None

            dias_sem_venda = row.get("dias_sem_venda")
            if pd.isna(dias_sem_venda):
                dias_sem_venda = None

            curva = row.get("Curva_ABCDE")
            if pd.isna(curva):
                curva = None

            produto = row.get("Descricao")
            if pd.isna(produto):
                produto = None

            empresa = row.get("Empresa")
            if pd.isna(empresa):
                empresa = None

            stock_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "codigo_produto": str(row["codigo_produto"]),
                "produto": produto,
                "empresa": empresa,
                "curva_abcde": curva,
                "estoque_atual": round(float(row["Quantidade_Estoque"]), 2),
                "valor_estoque": round(float(row["valor_estoque"]), 2),
                "qtd_vendida_30d": round(float(row["qtd_vendida_30d"]), 2),
                "faturamento_30d": round(float(row["faturamento_30d"]), 2),
                "qtd_vendida_90d": round(float(row["qtd_vendida_90d"]), 2),
                "faturamento_90d": round(float(row["faturamento_90d"]), 2),
                "ultima_venda": ultima_venda,
                "dias_sem_venda": None if dias_sem_venda is None else int(dias_sem_venda),
                "media_venda_mensal": round(float(row["media_venda_mensal"]), 4),
                "cobertura_estoque": None if cobertura is None else round(float(cobertura), 4),
                "risk_type": row["risk_type"],
                "status": row["status"]
            })

        self.supabase.replace_snapshot(
            "mart_stock_product_snapshot",
            filters,
            stock_records
        )

        status_counts = stock_df["status"].value_counts().to_dict()

        return {
            "stock_products": len(stock_records),
            "stock_critical": int(status_counts.get("critical", 0)),
            "stock_attention": int(status_counts.get("attention", 0)),
            "stock_healthy": int(status_counts.get("healthy", 0))
        }