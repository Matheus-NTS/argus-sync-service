class CommercialRecommendations:

    def build(self, facts):

        recommendations = []

        facts_by_type = {
            fact["fact_type"]: fact
            for fact in facts
        }

        concentration = facts_by_type.get("customer_concentration")

        if concentration and concentration["value"] >= 0.5:
            recommendations.append({
                "recommendation_type": "customer_risk",
                "priority": "high",
                "title": "Reduzir concentração de clientes",
                "description": (
                    "Acompanhar de perto os 3 maiores clientes do mês e buscar ampliar "
                    "a carteira ativa para reduzir dependência comercial."
                )
            })

        top_seller = facts_by_type.get("top_seller")

        if top_seller:
            recommendations.append({
                "recommendation_type": "seller_performance",
                "priority": "medium",
                "title": "Replicar boas práticas do vendedor destaque",
                "description": (
                    "Analisar a carteira, mix de produtos e abordagem comercial do vendedor "
                    "líder para identificar práticas que possam ser replicadas pela equipe."
                )
            })

        top_product = facts_by_type.get("top_product")

        if top_product:
            recommendations.append({
                "recommendation_type": "product_opportunity",
                "priority": "medium",
                "title": "Aproveitar produto em destaque",
                "description": (
                    "Avaliar disponibilidade, margem e oportunidades de campanha para o produto "
                    "com maior faturamento no mês."
                )
            })

        top_category = facts_by_type.get("top_category")

        if top_category:
            recommendations.append({
                "recommendation_type": "category_strategy",
                "priority": "medium",
                "title": "Fortalecer categoria principal",
                "description": (
                    "Acompanhar a categoria líder para entender se o crescimento vem de volume, "
                    "ticket médio ou concentração em poucos clientes."
                )
            })

        if not recommendations:
            recommendations.append({
                "recommendation_type": "general",
                "priority": "low",
                "title": "Manter acompanhamento comercial",
                "description": (
                    "Os indicadores atuais não apontam riscos críticos, mas o acompanhamento "
                    "diário deve ser mantido para identificar desvios rapidamente."
                )
            })

        return recommendations