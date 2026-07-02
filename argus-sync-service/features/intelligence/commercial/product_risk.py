class ProductRisk:

    def build(self, product_df, product_abc_df):

        risks = []

        if product_df is None or len(product_df) == 0:
            return risks

        if product_abc_df is None or len(product_abc_df) == 0:
            return risks

        abc_lookup = product_abc_df[[
            "prod_codigo",
            "classe"
        ]].copy()

        df = product_df.merge(
            abc_lookup,
            on="prod_codigo",
            how="left"
        )

        for _, row in df.iterrows():

            if row["classe"] == "A" and row["pedidos"] <= 1:
                risks.append({
                    "prod_codigo": str(row["prod_codigo"]),
                    "produto": row["produto"],
                    "risk_type": "high_value_low_frequency",
                    "severity": "high",
                    "description": (
                        f"Produto Classe A com alto faturamento, mas apenas {int(row['pedidos'])} pedido(s) no período. "
                        "Recomenda-se acompanhar recorrência e dependência de vendas pontuais."
                    )
                })

            if row["classe"] == "A" and row["clientes"] <= 2:
                risks.append({
                    "prod_codigo": str(row["prod_codigo"]),
                    "produto": row["produto"],
                    "risk_type": "low_customer_base",
                    "severity": "medium",
                    "description": (
                        f"Produto Classe A vendido para apenas {int(row['clientes'])} cliente(s). "
                        "Há risco de dependência e oportunidade de ampliar a base compradora."
                    )
                })

        return risks