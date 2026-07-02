class CustomerOverview:

    def build(self, customer_df, customer_abc_df, customer_risks, concentration_records):

        clientes_ativos = len(customer_df)

        faturamento_total = (
            float(customer_df["faturamento_total"].sum())
            if clientes_ativos > 0
            else 0
        )

        clientes_classe_a = len(customer_abc_df[customer_abc_df["classe"] == "A"])
        clientes_classe_b = len(customer_abc_df[customer_abc_df["classe"] == "B"])
        clientes_classe_c = len(customer_abc_df[customer_abc_df["classe"] == "C"])

        clientes_em_risco = len(customer_risks)

        top_cliente = None
        top_cliente_faturamento = 0

        if clientes_ativos > 0:
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

        if top_5_clientes_share >= 0.80:
            status = "critical"
        elif clientes_em_risco >= 25 or top_5_clientes_share >= 0.65:
            status = "attention"
        elif clientes_em_risco >= 10:
            status = "monitoring"
        else:
            status = "healthy"

        headline = (
            f"A carteira possui {clientes_ativos} clientes ativos no mês. "
            f"{clientes_classe_a} clientes estão na Classe A, "
            f"{clientes_em_risco} clientes exigem acompanhamento e os top 5 clientes "
            f"representam {top_5_clientes_share:.2%} do faturamento."
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