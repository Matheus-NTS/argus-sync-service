class CustomerRisk:

    def build(self, customer_df, customer_abc_df):

        risks = []

        if customer_df is None or len(customer_df) == 0:
            return risks

        if customer_abc_df is None or len(customer_abc_df) == 0:
            return risks

        lookup_cols = ["codigo_cliente", "classe"]
        merge_cols = ["codigo_cliente"]

        if "Empresa" in customer_df.columns and "Empresa" in customer_abc_df.columns:
            lookup_cols = ["Empresa", "codigo_cliente", "classe"]
            merge_cols = ["Empresa", "codigo_cliente"]

        abc_lookup = customer_abc_df[lookup_cols].copy()

        df = customer_df.merge(
            abc_lookup,
            on=merge_cols,
            how="left"
        )

        for _, row in df.iterrows():

            empresa = row["Empresa"] if "Empresa" in row else "TOTAL"

            if (
                row["classe"] == "A"
                and row["pedidos"] == 1
                and row["faturamento_total"] >= 2000
            ):
                risks.append({
                    "empresa": empresa,
                    "codigo_cliente": str(row["codigo_cliente"]),
                    "cliente": row["Cliente"],
                    "risk_type": "high_value_low_frequency",
                    "severity": "high",
                    "description": (
                        f"Cliente Classe A com faturamento relevante de "
                        f"R$ {row['faturamento_total']:,.2f}, mas apenas "
                        f"{int(row['pedidos'])} pedido no período. "
                        "Recomenda-se acompanhamento próximo para reduzir risco de compra pontual."
                    )
                })

            if (
                row["classe"] == "A"
                and row["mix_produtos"] == 1
            ):
                risks.append({
                    "empresa": empresa,
                    "codigo_cliente": str(row["codigo_cliente"]),
                    "cliente": row["Cliente"],
                    "risk_type": "low_product_mix",
                    "severity": "medium",
                    "description": (
                        f"Cliente Classe A com mix reduzido de apenas "
                        f"{int(row['mix_produtos'])} produto. "
                        "Há oportunidade de ampliar o relacionamento com venda cruzada."
                    )
                })

        return risks