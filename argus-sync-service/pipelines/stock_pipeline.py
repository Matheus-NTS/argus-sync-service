from datetime import datetime

import pandas as pd

from extractors.produto_extractor import ProdutoExtractor
from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer

from features.intelligence.stock.stock_snapshot import StockSnapshot
from features.intelligence.stock.stock_overview import StockOverview
from features.intelligence.stock.stock_scorecards import StockScorecards
from features.intelligence.stock.stock_risk import StockRisk
from features.intelligence.stock.stock_company import StockCompany


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

        # -------------------------
        # SNAPSHOT
        # -------------------------
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

            media_venda_mensal = row.get("media_venda_mensal")
            if pd.isna(media_venda_mensal):
                media_venda_mensal = 0

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
                "media_venda_mensal": round(float(media_venda_mensal), 4),
                "cobertura_estoque": None if cobertura is None else round(float(cobertura), 4),
                "risk_type": row["risk_type"],
                "status": row["status"]
            })

        self.supabase.replace_snapshot(
            "mart_stock_product_snapshot",
            filters,
            stock_records
        )

        # -------------------------
        # OVERVIEW / SCORECARDS / RISKS / COMPANY
        # -------------------------
        overview = StockOverview().build(stock_df)
        scorecards = StockScorecards().build(overview)
        risks = StockRisk().build(stock_df)
        company_snapshot = StockCompany().build(stock_df)

        overview_records = [{
            "reference_date": filters["reference_date"],
            "period_type": filters["period_type"],
            "sku_total": int(overview["sku_total"]),
            "sku_criticos": int(overview["sku_criticos"]),
            "sku_atencao": int(overview["sku_atencao"]),
            "sku_saudaveis": int(overview["sku_saudaveis"]),
            "valor_total_estoque": round(float(overview["valor_total_estoque"]), 2),
            "quantidade_total_estoque": round(float(overview["quantidade_total_estoque"]), 2),
            "rupturas": int(overview["rupturas"]),
            "sem_giro": int(overview["sem_giro"]),
            "excesso": int(overview["excesso"]),
            "headline": overview["headline"],
            "status": overview["status"]
        }]

        self.supabase.replace_snapshot(
            "mart_stock_overview",
            filters,
            overview_records
        )

        # -------------------------
        # SCORECARDS
        # -------------------------
        scorecard_records = []

        for card in scorecards:
            scorecard_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "card_key": card["card_key"],
                "label": card["label"],
                "value_numeric": None if card["value_numeric"] is None else round(float(card["value_numeric"]), 4),
                "value_text": card["value_text"],
                "value_type": card["value_type"],
                "status": card["status"],
                "sort_order": int(card["sort_order"])
            })

        self.supabase.replace_snapshot(
            "mart_stock_scorecards",
            filters,
            scorecard_records
        )

        # -------------------------
        # RISKS
        # -------------------------
        risk_records = []

        for risk in risks:

            ultima_venda = None
            if pd.notnull(risk.get("ultima_venda")):
                try:
                    ultima_venda = pd.to_datetime(risk["ultima_venda"]).date().isoformat()
                except Exception:
                    ultima_venda = None

            cobertura = risk.get("cobertura_estoque")
            if pd.isna(cobertura):
                cobertura = None

            dias_sem_venda = risk.get("dias_sem_venda")
            if pd.isna(dias_sem_venda):
                dias_sem_venda = None

            risk_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "codigo_produto": risk["codigo_produto"],
                "produto": risk["produto"],
                "empresa": risk["empresa"],
                "curva_abcde": risk["curva_abcde"],
                "estoque_atual": round(float(risk["estoque_atual"]), 2),
                "valor_estoque": round(float(risk["valor_estoque"]), 2),
                "qtd_vendida_90d": round(float(risk["qtd_vendida_90d"]), 2),
                "faturamento_90d": round(float(risk["faturamento_90d"]), 2),
                "ultima_venda": ultima_venda,
                "dias_sem_venda": None if dias_sem_venda is None else int(dias_sem_venda),
                "cobertura_estoque": None if cobertura is None else round(float(cobertura), 4),
                "risk_type": risk["risk_type"],
                "status": risk["status"],
                "description": risk["description"]
            })

        self.supabase.replace_snapshot(
            "mart_stock_risk",
            filters,
            risk_records
        )

        # -------------------------
        # COMPANY SNAPSHOT
        # -------------------------
        company_records = []

        for item in company_snapshot:
            company_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": item["empresa"],
                "sku_total": int(item["sku_total"]),
                "sku_criticos": int(item["sku_criticos"]),
                "sku_atencao": int(item["sku_atencao"]),
                "sku_saudaveis": int(item["sku_saudaveis"]),
                "quantidade_total_estoque": round(float(item["quantidade_total_estoque"]), 2),
                "valor_total_estoque": round(float(item["valor_total_estoque"]), 2),
                "rupturas": int(item["rupturas"]),
                "sem_giro": int(item["sem_giro"]),
                "excesso": int(item["excesso"]),
                "status": item["status"]
            })

        self.supabase.replace_snapshot(
            "mart_stock_company_snapshot",
            filters,
            company_records
        )

        status_counts = stock_df["status"].value_counts().to_dict()

        return {
            "stock_products": len(stock_records),
            "stock_critical": int(status_counts.get("critical", 0)),
            "stock_attention": int(status_counts.get("attention", 0)),
            "stock_healthy": int(status_counts.get("healthy", 0)),
            "stock_overview": len(overview_records),
            "stock_scorecards": len(scorecard_records),
            "stock_risks": len(risk_records),
            "stock_company": len(company_records),
            "stock_status": overview["status"]
        }