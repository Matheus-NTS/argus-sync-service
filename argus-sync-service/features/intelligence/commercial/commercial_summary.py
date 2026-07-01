class CommercialSummary:

    def build(self, facts):

        if not facts:
            return "Ainda não há dados comerciais suficientes para gerar uma análise executiva."

        facts_by_type = {
            fact["fact_type"]: fact
            for fact in facts
        }

        summary_parts = []

        top_seller = facts_by_type.get("top_seller")
        top_company = facts_by_type.get("top_company")
        top_product = facts_by_type.get("top_product")
        top_customer = facts_by_type.get("top_customer")
        top_category = facts_by_type.get("top_category")
        customer_concentration = facts_by_type.get("customer_concentration")

        summary_parts.append("Análise comercial do mês:")

        if top_company:
            summary_parts.append(top_company["description"])

        if top_seller:
            summary_parts.append(top_seller["description"])

        if top_category:
            summary_parts.append(top_category["description"])

        if top_product:
            summary_parts.append(top_product["description"])

        if top_customer:
            summary_parts.append(top_customer["description"])

        if customer_concentration:
            concentration_value = customer_concentration["value"]

            if concentration_value >= 0.5:
                summary_parts.append(
                    "A concentração de faturamento nos maiores clientes exige atenção, "
                    "pois indica dependência relevante de poucos compradores."
                )
            else:
                summary_parts.append(
                    "A distribuição de faturamento entre clientes está saudável, "
                    "sem concentração crítica nos três maiores compradores."
                )

        summary_parts.append(
            "Recomendação: acompanhar diariamente os principais vendedores, clientes e categorias "
            "para identificar rapidamente desvios, oportunidades e riscos comerciais."
        )

        return " ".join(summary_parts)