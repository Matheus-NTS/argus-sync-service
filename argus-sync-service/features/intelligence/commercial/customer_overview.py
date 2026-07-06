class CustomerOverview:

    def build(self, customer_df, customer_abc_df, customer_risks, concentration_records):

        clientes_ativos = len(customer_df)

        faturamento_total = (
            float(customer_df["faturamento_total"].sum())
            if clientes_ativos > 0 and "faturamento_total" in customer_df.columns
            else 0
        )

        clientes_classe_a = (
            len(customer_abc_df[customer_abc_df["classe"] == "A"])
            if "classe" in customer_abc_df.columns
            else 0
        )

        clientes_classe_b = (
            len(customer_abc_df[customer_abc_df["classe"] == "B"])
            if "classe" in customer_abc_df.columns
            else 0
        )

        clientes_classe_c = (
            len(customer_abc_df[customer_abc_df["classe"] == "C"])
            if "classe" in customer_abc_df.columns
            else 0
        )

        clientes_em_risco = len(customer_risks)

        top_cliente = None
        top_cliente_faturamento = 0

        if clientes_ativos > 0 and "faturamento_total" in customer_df.columns:
            top_row = customer_df.sort_values(
                by="faturamento_total",
                ascending=False
            ).iloc[0]

            top_cliente = top_row["Cliente"]
            top_cliente_faturamento = float(top_row["faturamento_total"])

        top_5_clientes_share = 0

        for item in concentration_records:
            if item["concentration_type"] == "customer" and item["top_n"] == 5:
                top_5_clientes_share = float(item["participation"])

        if clientes_ativos == 0:
            status = "healthy"
            headline = "Não houve clientes compradores neste período."
        elif top_5_clientes_share >= 0.80:
            status = "critical"
            headline = (
                f"A carteira teve {clientes_ativos} clientes ativos no período. "
                f"Os top 5 clientes representam {top_5_clientes_share:.2%} do faturamento."
            )
        elif clientes_em_risco >= 25 or top_5_clientes_share >= 0.65:
            status = "attention"
            headline = (
                f"A carteira teve {clientes_ativos} clientes ativos no período. "
                f"{clientes_classe_a} clientes estão na Classe A, "
                f"{clientes_em_risco} clientes exigem acompanhamento e os top 5 clientes "
                f"representam {top_5_clientes_share:.2%} do faturamento."
            )
        elif clientes_em_risco >= 10:
            status = "monitoring"
            headline = (
                f"A carteira teve {clientes_ativos} clientes ativos no período. "
                f"{clientes_em_risco} clientes exigem monitoramento."
            )
        else:
            status = "healthy"
            headline = (
                f"A carteira teve {clientes_ativos} clientes ativos no período. "
                f"{clientes_classe_a} clientes estão na Classe A."
            )

        return {
            "clientes_ativos": clientes_ativos,
            "clientes_classe_a": clientes_classe_a,
            "clientes_classe_b": clientes_classe_b,
            "clientes_classe_c": clientes_classe_c,
            "clientes_em_risco": clientes_em_risco,
            "faturamento_total": faturamento_total,
            "top_cliente": top_cliente,
            "top_cliente_faturamento": top_cliente_faturamento,
            "top_5_clientes_share": top_5_clientes_share,
            "headline": headline,
            "status": status
        }