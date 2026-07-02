from datetime import datetime

from features.intelligence.commercial.commercial_facts import CommercialFacts
from features.intelligence.commercial.commercial_summary import CommercialSummary
from features.intelligence.commercial.commercial_recommendations import CommercialRecommendations
from features.intelligence.commercial.commercial_alerts import CommercialAlerts
from features.intelligence.commercial.abc_analysis import ABCAnalysis
from features.intelligence.commercial.customer_abc_analysis import CustomerABCAnalysis
from features.intelligence.commercial.concentration_analysis import ConcentrationAnalysis


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

        self.supabase.replace_snapshot(
            "mart_commercial_facts",
            filters,
            fact_records
        )

        # -------------------------
        # SUMMARY
        # -------------------------
        summary_records = [{
            "reference_date": filters["reference_date"],
            "period_type": filters["period_type"],
            "summary": CommercialSummary().build(facts)
        }]

        self.supabase.replace_snapshot(
            "mart_commercial_summary",
            filters,
            summary_records
        )

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

        return {
            "commercial_facts": len(fact_records),
            "commercial_summary": len(summary_records),
            "commercial_recommendations": len(recommendation_records),
            "commercial_alerts": len(alert_records),
            "abc_products": len(product_abc_records),
            "abc_customers": len(customer_abc_records),
            "commercial_concentration": len(concentration_records)
        }