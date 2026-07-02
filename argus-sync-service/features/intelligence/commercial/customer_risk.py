class CustomerRisk:

    def build(self, customer_df, customer_abc_df):

        risks = []

        if customer_df is None or len(customer_df) == 0:
            return risks

        if customer_abc_df is None or len(customer_abc_df) == 0:
            return risks

        abc_lookup = customer_abc_df[[
            "codigo_cliente",
            "classe"
        ]].copy()

        df = customer_df.merge(
            abc_lookup,
            on="codigo_cliente",
            how="left"
        )

        for _, row in df.iterrows():

            if row["classe"] == "A" and row["pedidos"] <= 1:
                risks.append({
                    "codigo_cliente": str(row["codigo_cliente"]),
                    "cliente": row["Cliente"],
                    "risk_type": "high_value_low_frequency",
                    "severity": "high",
                    "description": (
                        f"Cliente Classe A com alto faturamento, mas apenas {int(row['pedidos'])} pedido(s) no período. "
                        "Recomenda-se acompanhamento próximo para reduzir risco de dependência pontual."
                    )
                })

            if row["classe"] == "A" and row["mix_produtos"] <= 2:
                risks.append({
                    "codigo_cliente": str(row["codigo_cliente"]),
                    "cliente": row["Cliente"],
                    "risk_type": "low_product_mix",
                    "severity": "medium",
                    "description": (
                        f"Cliente Classe A com mix reduzido de {int(row['mix_produtos'])} produto(s). "
                        "Há oportunidade de ampliar o relacionamento com venda cruzada."
                    )
                })

        return risks