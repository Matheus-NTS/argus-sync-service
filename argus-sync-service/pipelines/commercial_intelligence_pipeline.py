from datetime import datetime

from features.intelligence.commercial.commercial_facts import CommercialFacts
from features.intelligence.commercial.commercial_summary import CommercialSummary
from features.intelligence.commercial.commercial_recommendations import CommercialRecommendations
from features.intelligence.commercial.commercial_alerts import CommercialAlerts
from features.intelligence.commercial.abc_analysis import ABCAnalysis
from features.intelligence.commercial.customer_abc_analysis import CustomerABCAnalysis
from features.intelligence.commercial.concentration_analysis import ConcentrationAnalysis
from features.intelligence.commercial.customer_risk import CustomerRisk
from features.intelligence.commercial.product_risk import ProductRisk
from features.intelligence.commercial.commercial_overview import CommercialOverview
from features.intelligence.commercial.commercial_scorecards import CommercialScorecards
from features.intelligence.commercial.product_overview import ProductOverview
from features.intelligence.commercial.product_scorecards import ProductScorecards
from features.intelligence.commercial.customer_overview import CustomerOverview
from features.intelligence.commercial.customer_scorecards import CustomerScorecards


class CommercialIntelligencePipeline:

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

    def run(self, ranking_df, company_df, product_df, customer_df, category_df):

        hoje = datetime.today()
        filters = {
            "reference_date": hoje.date().isoformat(),
            "period_type": "current_month"
        }

        facts = CommercialFacts().build(
            ranking_df,
            company_df,
            product_df,
            customer_df,
            category_df
        )

        product_abc_df = ABCAnalysis().build(product_df)
        customer_abc_df = CustomerABCAnalysis().build(customer_df)

        concentration_records_raw = ConcentrationAnalysis().build(
            customer_df,
            product_df
        )

        recommendations = CommercialRecommendations().build(
            facts,
            product_abc_df,
            customer_abc_df,
            concentration_records_raw
        )

        alerts = CommercialAlerts().build(concentration_records_raw)

        customer_risks = CustomerRisk().build(
            customer_df,
            customer_abc_df
        )

        product_risks = ProductRisk().build(
            product_df,
            product_abc_df
        )

        overview = CommercialOverview().build(
            ranking_df=ranking_df,
            product_df=product_df,
            customer_df=customer_df,
            category_df=category_df,
            concentration_records=concentration_records_raw,
            alerts=alerts,
            customer_risks=customer_risks,
            product_risks=product_risks,
            recommendations=recommendations
        )

        scorecards = CommercialScorecards().build(overview)

        product_overview = ProductOverview().build(
            product_df=product_df,
            product_abc_df=product_abc_df,
            product_risks=product_risks,
            concentration_records=concentration_records_raw
        )

        product_scorecards = ProductScorecards().build(product_overview)

        customer_overview = CustomerOverview().build(
            customer_df=customer_df,
            customer_abc_df=customer_abc_df,
            customer_risks=customer_risks,
            concentration_records=concentration_records_raw
        )

        customer_scorecards = CustomerScorecards().build(customer_overview)

        # -------------------------
        # FACTS
        # -------------------------
        fact_records = []
        for fact in facts:
            fact_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "fact_type": fact["fact_type"],
                "severity": fact["severity"],
                "title": fact["title"],
                "description": fact["description"],
                "value": round(float(fact["value"]), 4)
            })

        self.supabase.replace_snapshot("mart_commercial_facts", filters, fact_records)

        # -------------------------
        # SUMMARY
        # -------------------------
        summary_records = [{
            "reference_date": filters["reference_date"],
            "period_type": filters["period_type"],
            "summary": CommercialSummary().build(facts)
        }]

        self.supabase.replace_snapshot("mart_commercial_summary", filters, summary_records)

        # -------------------------
        # RECOMMENDATIONS
        # -------------------------
        recommendation_records = []
        for recommendation in recommendations:
            recommendation_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "recommendation_type": recommendation["recommendation_type"],
                "priority": recommendation["priority"],
                "title": recommendation["title"],
                "description": recommendation["description"]
            })

        self.supabase.replace_snapshot(
            "mart_commercial_recommendations",
            filters,
            recommendation_records
        )

        # -------------------------
        # ALERTS
        # -------------------------
        alert_records = []
        for alert in alerts:
            alert_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "alert_type": alert["alert_type"],
                "severity": alert["severity"],
                "title": alert["title"],
                "description": alert["description"]
            })

        self.supabase.replace_snapshot(
            "mart_commercial_alerts",
            filters,
            alert_records
        )

        # -------------------------
        # PRODUCT ABC
        # -------------------------
        product_abc_records = []
        for _, row in product_abc_df.iterrows():
            product_abc_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "prod_codigo": row["prod_codigo"],
                "produto": row["produto"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "percentual": round(float(row["percentual"]), 4),
                "percentual_acumulado": round(float(row["percentual_acumulado"]), 4),
                "classe": row["classe"],
                "ranking": int(row["ranking"])
            })

        self.supabase.replace_snapshot(
            "mart_sales_product_abc_snapshot",
            filters,
            product_abc_records
        )

        # -------------------------
        # CUSTOMER ABC
        # -------------------------
        customer_abc_records = []
        for _, row in customer_abc_df.iterrows():
            customer_abc_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "codigo_cliente": str(row["codigo_cliente"]),
                "cliente": row["Cliente"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "percentual": round(float(row["percentual"]), 4),
                "percentual_acumulado": round(float(row["percentual_acumulado"]), 4),
                "classe": row["classe"],
                "ranking": int(row["ranking"])
            })

        self.supabase.replace_snapshot(
            "mart_sales_customer_abc_snapshot",
            filters,
            customer_abc_records
        )

        # -------------------------
        # CONCENTRATION
        # -------------------------
        concentration_records = []
        for row in concentration_records_raw:
            concentration_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "concentration_type": row["concentration_type"],
                "top_n": int(row["top_n"]),
                "participation": round(float(row["participation"]), 4),
                "description": row["description"]
            })

        self.supabase.replace_snapshot(
            "mart_commercial_concentration_snapshot",
            filters,
            concentration_records
        )

        # -------------------------
        # CUSTOMER RISK
        # -------------------------
        customer_risk_records = []
        for risk in customer_risks:
            customer_risk_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "codigo_cliente": risk["codigo_cliente"],
                "cliente": risk["cliente"],
                "risk_type": risk["risk_type"],
                "severity": risk["severity"],
                "description": risk["description"]
            })

        self.supabase.replace_snapshot(
            "mart_commercial_customer_risk",
            filters,
            customer_risk_records
        )

        # -------------------------
        # PRODUCT RISK
        # -------------------------
        product_risk_records = []
        for risk in product_risks:
            product_risk_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "prod_codigo": risk["prod_codigo"],
                "produto": risk["produto"],
                "risk_type": risk["risk_type"],
                "severity": risk["severity"],
                "description": risk["description"]
            })

        self.supabase.replace_snapshot(
            "mart_commercial_product_risk",
            filters,
            product_risk_records
        )

        # -------------------------
        # COMMERCIAL OVERVIEW
        # -------------------------
        overview_records = [{
            "reference_date": filters["reference_date"],
            "period_type": filters["period_type"],
            "faturamento_total": round(float(overview["faturamento_total"]), 2),
            "clientes_ativos": int(overview["clientes_ativos"]),
            "produtos_ativos": int(overview["produtos_ativos"]),
            "categorias_ativas": int(overview["categorias_ativas"]),
            "vendedores_ativos": int(overview["vendedores_ativos"]),
            "ticket_medio": round(float(overview["ticket_medio"]), 2),
            "top_cliente_share": round(float(overview["top_cliente_share"]), 4),
            "top_5_clientes_share": round(float(overview["top_5_clientes_share"]), 4),
            "top_produto_share": round(float(overview["top_produto_share"]), 4),
            "top_5_produtos_share": round(float(overview["top_5_produtos_share"]), 4),
            "alertas_count": int(overview["alertas_count"]),
            "customer_risks_count": int(overview["customer_risks_count"]),
            "product_risks_count": int(overview["product_risks_count"]),
            "recommendations_count": int(overview["recommendations_count"]),
            "headline": overview["headline"],
            "status": overview["status"]
        }]

        self.supabase.replace_snapshot(
            "mart_commercial_overview",
            filters,
            overview_records
        )

        # -------------------------
        # COMMERCIAL SCORECARDS
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
            "mart_commercial_scorecards",
            filters,
            scorecard_records
        )

        # -------------------------
        # PRODUCT OVERVIEW
        # -------------------------
        product_overview_records = [{
            "reference_date": filters["reference_date"],
            "period_type": filters["period_type"],
            "produtos_ativos": int(product_overview["produtos_ativos"]),
            "produtos_classe_a": int(product_overview["produtos_classe_a"]),
            "produtos_classe_b": int(product_overview["produtos_classe_b"]),
            "produtos_classe_c": int(product_overview["produtos_classe_c"]),
            "produtos_em_risco": int(product_overview["produtos_em_risco"]),
            "faturamento_total": round(float(product_overview["faturamento_total"]), 2),
            "top_produto": product_overview["top_produto"],
            "top_produto_faturamento": round(float(product_overview["top_produto_faturamento"]), 2),
            "top_5_produtos_share": round(float(product_overview["top_5_produtos_share"]), 4),
            "headline": product_overview["headline"],
            "status": product_overview["status"]
        }]

        self.supabase.replace_snapshot(
            "mart_product_overview",
            filters,
            product_overview_records
        )

        # -------------------------
        # PRODUCT SCORECARDS
        # -------------------------
        product_scorecard_records = []
        for card in product_scorecards:
            product_scorecard_records.append({
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
            "mart_product_scorecards",
            filters,
            product_scorecard_records
        )

        # -------------------------
        # CUSTOMER OVERVIEW
        # -------------------------
        customer_overview_records = [{
            "reference_date": filters["reference_date"],
            "period_type": filters["period_type"],
            "clientes_ativos": int(customer_overview["clientes_ativos"]),
            "clientes_classe_a": int(customer_overview["clientes_classe_a"]),
            "clientes_classe_b": int(customer_overview["clientes_classe_b"]),
            "clientes_classe_c": int(customer_overview["clientes_classe_c"]),
            "clientes_em_risco": int(customer_overview["clientes_em_risco"]),
            "faturamento_total": round(float(customer_overview["faturamento_total"]), 2),
            "top_cliente": customer_overview["top_cliente"],
            "top_cliente_faturamento": round(float(customer_overview["top_cliente_faturamento"]), 2),
            "top_5_clientes_share": round(float(customer_overview["top_5_clientes_share"]), 4),
            "headline": customer_overview["headline"],
            "status": customer_overview["status"]
        }]

        self.supabase.replace_snapshot(
            "mart_customer_overview",
            filters,
            customer_overview_records
        )

        # -------------------------
        # CUSTOMER SCORECARDS
        # -------------------------
        customer_scorecard_records = []
        for card in customer_scorecards:
            customer_scorecard_records.append({
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
            "mart_customer_scorecards",
            filters,
            customer_scorecard_records
        )

        return {
            "commercial_facts": len(fact_records),
            "commercial_summary": len(summary_records),
            "commercial_recommendations": len(recommendation_records),
            "commercial_alerts": len(alert_records),
            "abc_products": len(product_abc_records),
            "abc_customers": len(customer_abc_records),
            "commercial_concentration": len(concentration_records),
            "customer_risks": len(customer_risk_records),
            "product_risks": len(product_risk_records),
            "commercial_overview": len(overview_records),
            "commercial_scorecards": len(scorecard_records),
            "product_overview": len(product_overview_records),
            "product_scorecards": len(product_scorecard_records),
            "customer_overview": len(customer_overview_records),
            "customer_scorecards": len(customer_scorecard_records),
            "commercial_status": overview["status"],
            "product_status": product_overview["status"],
            "customer_status": customer_overview["status"]
        }