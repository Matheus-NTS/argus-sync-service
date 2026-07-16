class ProductRisk:

    def build(self, product_df, product_abc_df):

        risks = []

        if product_df is None or len(product_df) == 0:
            return risks

        if product_abc_df is None or len(product_abc_df) == 0:
            return risks

        lookup_cols = ["prod_codigo", "classe"]
        merge_cols = ["prod_codigo"]

        if "Empresa" in product_df.columns and "Empresa" in product_abc_df.columns:
            lookup_cols = ["Empresa", "prod_codigo", "classe"]
            merge_cols = ["Empresa", "prod_codigo"]

        abc_lookup = product_abc_df[lookup_cols].copy()

        df = product_df.merge(
            abc_lookup,
            on=merge_cols,
            how="left"
        )

        for _, row in df.iterrows():

            empresa = row["Empresa"] if "Empresa" in row else "TOTAL"

            if (
                row["classe"] == "A"
                and row["pedidos"] == 1
                and row["faturamento_total"] >= 1500
            ):
                risks.append({
                    "empresa": empresa,
                    "prod_codigo": str(row["prod_codigo"]),
                    "produto": row["produto"],
                    "risk_type": "high_value_low_frequency",
                    "severity": "high",
                    "description": (
                        f"Produto Classe A com faturamento relevante de "
                        f"R$ {row['faturamento_total']:,.2f}, mas apenas "
                        f"{int(row['pedidos'])} pedido no período. "
                        "Recomenda-se acompanhar recorrência e dependência de vendas pontuais."
                    )
                })

            if (
                row["classe"] == "A"
                and row["clientes"] == 1
            ):
                risks.append({
                    "empresa": empresa,
                    "prod_codigo": str(row["prod_codigo"]),
                    "produto": row["produto"],
                    "risk_type": "low_customer_base",
                    "severity": "medium",
                    "description": (
                        f"Produto Classe A vendido para apenas "
                        f"{int(row['clientes'])} cliente. "
                        "Há risco de dependência e oportunidade de ampliar a base compradora."
                    )
                })

        return risks