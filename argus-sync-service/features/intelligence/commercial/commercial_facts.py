class CommercialFacts:

    def build(self, seller_df, company_df, product_df, customer_df, category_df):

        facts = []

        if len(seller_df) > 0:
            top_seller = seller_df.iloc[0]

            facts.append({
                "fact_type": "top_seller",
                "severity": "success",
                "title": "Vendedor líder",
                "description": (
                    f"{top_seller['Vendedor']} lidera o mês com "
                    f"R$ {top_seller['faturamento_total']:,.2f} em faturamento."
                ),
                "value": float(top_seller["faturamento_total"])
            })

        if len(company_df) > 0:
            top_company = company_df.iloc[0]

            facts.append({
                "fact_type": "top_company",
                "severity": "success",
                "title": "Empresa líder",
                "description": (
                    f"{top_company['Empresa']} lidera o faturamento do mês com "
                    f"R$ {top_company['faturamento_total']:,.2f}."
                ),
                "value": float(top_company["faturamento_total"])
            })

        if len(product_df) > 0:
            top_product = product_df.iloc[0]

            facts.append({
                "fact_type": "top_product",
                "severity": "info",
                "title": "Produto destaque",
                "description": (
                    f"{top_product['produto']} é o produto com maior faturamento no mês, "
                    f"somando R$ {top_product['faturamento_total']:,.2f}."
                ),
                "value": float(top_product["faturamento_total"])
            })

        if len(customer_df) > 0:
            top_customer = customer_df.iloc[0]

            facts.append({
                "fact_type": "top_customer",
                "severity": "info",
                "title": "Cliente destaque",
                "description": (
                    f"{top_customer['Cliente']} é o maior cliente do mês, com "
                    f"R$ {top_customer['faturamento_total']:,.2f} em compras."
                ),
                "value": float(top_customer["faturamento_total"])
            })

        if len(category_df) > 0:
            top_category = category_df.iloc[0]

            facts.append({
                "fact_type": "top_category",
                "severity": "info",
                "title": "Categoria destaque",
                "description": (
                    f"{top_category['Categoria']} é a principal categoria do mês, com "
                    f"R$ {top_category['faturamento_total']:,.2f}."
                ),
                "value": float(top_category["faturamento_total"])
            })

        if len(customer_df) >= 3:
            total_revenue = customer_df["faturamento_total"].sum()
            top_3_revenue = customer_df.head(3)["faturamento_total"].sum()

            concentration = top_3_revenue / total_revenue if total_revenue > 0 else 0

            severity = "warning" if concentration >= 0.5 else "info"

            facts.append({
                "fact_type": "customer_concentration",
                "severity": severity,
                "title": "Concentração de clientes",
                "description": (
                    f"Os 3 maiores clientes representam {concentration:.2%} "
                    f"do faturamento do mês."
                ),
                "value": float(concentration)
            })

        return facts