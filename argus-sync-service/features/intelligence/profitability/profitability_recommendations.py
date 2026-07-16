class ProfitabilityRecommendations:

    def build(self, dimensions, overview, risks):

        recommendations = []

        products = dimensions.get("product", [])
        categories = dimensions.get("category", [])
        customers = dimensions.get("customer", [])

        profitable_products = sorted(
            [
                item
                for item in products
                if item.get("lucro", 0) > 0
            ],
            key=lambda item: item["lucro"],
            reverse=True
        )

        if profitable_products:

            top = profitable_products[0]

            recommendations.append({
                "recommendation_type": "protect_top_profit_product",
                "priority": "high",
                "dimension_type": "product",
                "dimension_key": top["dimension_key"],
                "dimension_value": top["dimension_value"],
                "evidence_value": top["lucro"],
                "title": "Proteger disponibilidade do produto líder",
                "description": (
                    f"{top['dimension_value']} lidera o lucro bruto "
                    "da operação no período."
                ),
                "action": (
                    "Priorizar disponibilidade, reposição e acompanhamento "
                    "de preço deste item."
                ),
            })

        low_margin_products = sorted(
            [
                item
                for item in products
                if (
                    item.get("margem_percentual") is not None
                    and item["margem_percentual"] < 10
                    and item.get("faturamento", 0) > 0
                )
            ],
            key=lambda item: item["faturamento"],
            reverse=True
        )

        if low_margin_products:

            item = low_margin_products[0]

            recommendations.append({
                "recommendation_type": "review_high_revenue_low_margin",
                "priority": "high",
                "dimension_type": "product",
                "dimension_key": item["dimension_key"],
                "dimension_value": item["dimension_value"],
                "evidence_value": item["faturamento"],
                "title": "Revisar produto de alto volume e baixa margem",
                "description": (
                    f"{item['dimension_value']} possui faturamento relevante "
                    f"e margem de {item['margem_percentual']:.2f}%."
                ),
                "action": (
                    "Revisar custo, preço, descontos e condições comerciais."
                ),
            })

        profitable_categories = sorted(
            [
                item
                for item in categories
                if item.get("lucro", 0) > 0
            ],
            key=lambda item: item["lucro"],
            reverse=True
        )

        if profitable_categories:

            item = profitable_categories[0]

            recommendations.append({
                "recommendation_type": "expand_profitable_category",
                "priority": "medium",
                "dimension_type": "category",
                "dimension_key": item["dimension_key"],
                "dimension_value": item["dimension_value"],
                "evidence_value": item["lucro"],
                "title": "Expandir categoria rentável",
                "description": (
                    f"{item['dimension_value']} é a categoria com maior "
                    "contribuição de lucro no período."
                ),
                "action": (
                    "Avaliar campanhas, disponibilidade e expansão do mix."
                ),
            })

        low_margin_customers = sorted(
            [
                item
                for item in customers
                if (
                    item.get("margem_percentual") is not None
                    and item["margem_percentual"]
                    < overview.get("margem_percentual", 0) - 10
                    and item.get("participacao_faturamento", 0) >= 0.02
                )
            ],
            key=lambda item: item["faturamento"],
            reverse=True
        )

        if low_margin_customers:

            item = low_margin_customers[0]

            recommendations.append({
                "recommendation_type": "review_customer_profitability",
                "priority": "medium",
                "dimension_type": "customer",
                "dimension_key": item["dimension_key"],
                "dimension_value": item["dimension_value"],
                "evidence_value": item["faturamento"],
                "title": "Revisar rentabilidade de cliente relevante",
                "description": (
                    f"{item['dimension_value']} possui faturamento relevante, "
                    f"mas margem de {item['margem_percentual']:.2f}%."
                ),
                "action": (
                    "Reavaliar descontos, mix e condições comerciais."
                ),
            })

        if overview.get("cobertura_financeira", 1) < 0.97:

            recommendations.append({
                "recommendation_type": "improve_cost_coverage",
                "priority": "medium",
                "dimension_type": "quality",
                "dimension_key": "cost_coverage",
                "dimension_value": "Cobertura de custos",
                "evidence_value": overview["cobertura_financeira"],
                "title": "Melhorar cobertura financeira",
                "description": (
                    f"A cobertura financeira está em "
                    f"{overview['cobertura_financeira'] * 100:.2f}%."
                ),
                "action": (
                    "Revisar produtos sem custo válido e cadastros "
                    "fora do escopo."
                ),
            })

        return recommendations[:10]