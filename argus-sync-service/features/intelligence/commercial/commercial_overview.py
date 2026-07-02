class CommercialOverview:

    def build(
        self,
        ranking_df,
        product_df,
        customer_df,
        category_df,
        concentration_records,
        alerts,
        customer_risks,
        product_risks,
        recommendations
    ):

        faturamento_total = float(product_df["faturamento_total"].sum()) if len(product_df) > 0 else 0

        clientes_ativos = len(customer_df)
        produtos_ativos = len(product_df)
        categorias_ativas = len(category_df)
        vendedores_ativos = len(ranking_df)

        pedidos_total = int(product_df["pedidos"].sum()) if len(product_df) > 0 else 0
        ticket_medio = faturamento_total / pedidos_total if pedidos_total > 0 else 0

        top_cliente_share = 0
        top_5_clientes_share = 0
        top_produto_share = 0
        top_5_produtos_share = 0

        for item in concentration_records:
            if item["concentration_type"] == "customer" and item["top_n"] == 3:
                top_cliente_share = float(item["participation"])

            if item["concentration_type"] == "customer" and item["top_n"] == 5:
                top_5_clientes_share = float(item["participation"])

            if item["concentration_type"] == "product" and item["top_n"] == 3:
                top_produto_share = float(item["participation"])

            if item["concentration_type"] == "product" and item["top_n"] == 5:
                top_5_produtos_share = float(item["participation"])

        alertas_count = len(alerts)
        customer_risks_count = len(customer_risks)
        product_risks_count = len(product_risks)
        recommendations_count = len(recommendations)

        total_risks = customer_risks_count + product_risks_count

        if alertas_count >= 3 or top_5_clientes_share >= 0.75 or top_5_produtos_share >= 0.75:
            status = "critical"
        elif total_risks >= 35 or alertas_count >= 2:
            status = "attention"
        elif total_risks >= 15 or alertas_count >= 1:
            status = "monitoring"
        else:
            status = "healthy"

        headline = (
            f"O Comercial possui {clientes_ativos} clientes ativos, "
            f"{produtos_ativos} produtos vendidos e {vendedores_ativos} vendedores ativos no mês. "
            f"Foram identificados {total_risks} riscos comerciais, "
            f"{alertas_count} alerta(s) e {recommendations_count} recomendações."
        )

        return {
            "faturamento_total": faturamento_total,
            "clientes_ativos": clientes_ativos,
            "produtos_ativos": produtos_ativos,
            "categorias_ativas": categorias_ativas,
            "vendedores_ativos": vendedores_ativos,
            "ticket_medio": ticket_medio,
            "top_cliente_share": top_cliente_share,
            "top_5_clientes_share": top_5_clientes_share,
            "top_produto_share": top_produto_share,
            "top_5_produtos_share": top_5_produtos_share,
            "alertas_count": alertas_count,
            "customer_risks_count": customer_risks_count,
            "product_risks_count": product_risks_count,
            "recommendations_count": recommendations_count,
            "headline": headline,
            "status": status
        }