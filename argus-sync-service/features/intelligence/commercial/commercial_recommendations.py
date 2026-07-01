class CommercialRecommendations:

    def build(self, facts, product_abc_df=None, customer_abc_df=None):

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
                    "Os maiores clientes concentram parte relevante do faturamento. "
                    "Acompanhe a carteira de clientes Classe A e desenvolva novos compradores para reduzir dependência."
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
                        f"{len(class_a_customers)} clientes estão na Classe A e sustentam a maior parte do faturamento. "
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