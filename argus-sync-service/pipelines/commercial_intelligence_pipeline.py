from datetime import datetime

from features.intelligence.commercial.commercial_facts import CommercialFacts
from features.intelligence.commercial.commercial_summary import CommercialSummary
from features.intelligence.commercial.commercial_recommendations import CommercialRecommendations
from features.intelligence.commercial.abc_analysis import ABCAnalysis


class CommercialIntelligencePipeline:

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

    def run(self, ranking_df, company_df, product_df, customer_df, category_df):

        hoje = datetime.today()

        commercial_facts = CommercialFacts()
        facts = commercial_facts.build(
            ranking_df,
            company_df,
            product_df,
            customer_df,
            category_df
        )

        fact_records = []

        for fact in facts:
            fact_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
                "fact_type": fact["fact_type"],
                "severity": fact["severity"],
                "title": fact["title"],
                "description": fact["description"],
                "value": round(float(fact["value"]), 4)
            })

        self.supabase.replace_snapshot(
            "mart_commercial_facts",
            {"reference_date": hoje.date().isoformat(), "period_type": "current_month"},
            fact_records
        )

        commercial_summary = CommercialSummary()
        summary_text = commercial_summary.build(facts)

        summary_records = [{
            "reference_date": hoje.date().isoformat(),
            "period_type": "current_month",
            "summary": summary_text
        }]

        self.supabase.replace_snapshot(
            "mart_commercial_summary",
            {"reference_date": hoje.date().isoformat(), "period_type": "current_month"},
            summary_records
        )

        commercial_recommendations = CommercialRecommendations()
        recommendations = commercial_recommendations.build(facts)

        recommendation_records = []

        for recommendation in recommendations:
            recommendation_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
                "recommendation_type": recommendation["recommendation_type"],
                "priority": recommendation["priority"],
                "title": recommendation["title"],
                "description": recommendation["description"]
            })

        self.supabase.replace_snapshot(
            "mart_commercial_recommendations",
            {"reference_date": hoje.date().isoformat(), "period_type": "current_month"},
            recommendation_records
        )

        abc = ABCAnalysis()
        abc_df = abc.build(product_df)

        abc_records = []

        for _, row in abc_df.iterrows():
            abc_records.append({
                "reference_date": hoje.date().isoformat(),
                "period_type": "current_month",
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
            {"reference_date": hoje.date().isoformat(), "period_type": "current_month"},
            abc_records
        )

        return {
            "commercial_facts": len(fact_records),
            "commercial_summary": len(summary_records),
            "commercial_recommendations": len(recommendation_records),
            "abc_products": len(abc_records)
        }