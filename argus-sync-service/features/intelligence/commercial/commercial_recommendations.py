class CommercialRecommendations:

    def build(self, facts, product_abc_df=None, customer_abc_df=None, concentration_records=None):

        recommendations = []

        facts_by_type = {
            fact["fact_type"]: fact
            for fact in facts
        }

        concentration_records = concentration_records or []

        customer_top_5 = next(
            (
                item for item in concentration_records
                if item["concentration_type"] == "customer" and item["top_n"] == 5
            ),
            None
        )

        product_top_5 = next(
            (
                item for item in concentration_records
                if item["concentration_type"] == "product" and item["top_n"] == 5
            ),
            None
        )

        if customer_top_5 and customer_top_5["participation"] >= 0.6:
            recommendations.append({
                "recommendation_type": "customer_concentration",
                "priority": "high",
                "title": "Reduzir dependência dos principais clientes",
                "description": (
                    f"Os top 5 clientes representam {customer_top_5['participation']:.2%} "
                    "do faturamento do mês. Recomenda-se ampliar a base ativa e criar ações "
                    "para reduzir dependência dos maiores compradores."
                )
            })

        if product_top_5 and product_top_5["participation"] >= 0.6:
            recommendations.append({
                "recommendation_type": "product_concentration",
                "priority": "high",
                "title": "Monitorar concentração em poucos produtos",
                "description": (
                    f"Os top 5 produtos representam {product_top_5['participation']:.2%} "
                    "do faturamento do mês. Garanta disponibilidade, margem e alternativas "
                    "para reduzir risco de dependência."
                )
            })

        if customer_abc_df is not None and len(customer_abc_df) > 0:
            class_a_customers = customer_abc_df[customer_abc_df["classe"] == "A"]

            if len(class_a_customers) > 0:
                recommendations.append({
                    "recommendation_type": "customer_abc",
                    "priority": "high",
                    "title": "Proteger clientes Classe A",
                    "description": (
                        f"{len(class_a_customers)} clientes estão na Classe A. "
                        "Priorize relacionamento, disponibilidade e acompanhamento comercial desses clientes."
                    )
                })

        if product_abc_df is not None and len(product_abc_df) > 0:
            class_a_products = product_abc_df[product_abc_df["classe"] == "A"]
            class_c_products = product_abc_df[product_abc_df["classe"] == "C"]

            if len(class_a_products) > 0:
                recommendations.append({
                    "recommendation_type": "product_abc",
                    "priority": "high",
                    "title": "Garantir disponibilidade dos produtos Classe A",
                    "description": (
                        f"{len(class_a_products)} produtos estão na Classe A. "
                        "Garanta estoque, preço competitivo e atenção comercial nesses itens."
                    )
                })

            if len(class_c_products) > len(class_a_products):
                recommendations.append({
                    "recommendation_type": "product_mix",
                    "priority": "medium",
                    "title": "Revisar produtos Classe C",
                    "description": (
                        f"{len(class_c_products)} produtos estão na Classe C. "
                        "Avalie baixa saída, margem, estoque parado e necessidade de campanhas específicas."
                    )
                })

        top_seller = facts_by_type.get("top_seller")

        if top_seller:
            recommendations.append({
                "recommendation_type": "seller_performance",
                "priority": "medium",
                "title": "Replicar boas práticas do vendedor destaque",
                "description": (
                    "Analise a carteira, mix de produtos e abordagem comercial do vendedor líder "
                    "para identificar práticas que possam ser replicadas pela equipe."
                )
            })

        if not recommendations:
            recommendations.append({
                "recommendation_type": "general",
                "priority": "low",
                "title": "Manter acompanhamento comercial",
                "description": (
                    "Os indicadores atuais não apontam riscos críticos, mas o acompanhamento diário deve ser mantido."
                )
            })

        return recommendations