class ProductOverview:

    def build(self, product_df, product_abc_df, product_risks, concentration_records):

        produtos_ativos = len(product_df)

        faturamento_total = (
            float(product_df["faturamento_total"].sum())
            if produtos_ativos > 0
            else 0
        )

        produtos_classe_a = len(product_abc_df[product_abc_df["classe"] == "A"])
        produtos_classe_b = len(product_abc_df[product_abc_df["classe"] == "B"])
        produtos_classe_c = len(product_abc_df[product_abc_df["classe"] == "C"])

        produtos_em_risco = len(product_risks)

        top_produto = None
        top_produto_faturamento = 0

        if produtos_ativos > 0:
            top_row = product_df.sort_values(
                by="faturamento_total",
                ascending=False
            ).iloc[0]

            top_produto = top_row["produto"]
            top_produto_faturamento = float(top_row["faturamento_total"])

        top_5_produtos_share = 0

        for item in concentration_records:
            if item["concentration_type"] == "product" and item["top_n"] == 5:
                top_5_produtos_share = float(item["participation"])

        if top_5_produtos_share >= 0.80:
            status = "critical"
        elif produtos_em_risco >= 30 or top_5_produtos_share >= 0.65:
            status = "attention"
        elif produtos_em_risco >= 12:
            status = "monitoring"
        else:
            status = "healthy"

        headline = (
            f"O portfólio teve {produtos_ativos} produtos ativos no mês. "
            f"{produtos_classe_a} produtos estão na Classe A, "
            f"{produtos_em_risco} produtos exigem acompanhamento e os top 5 produtos "
            f"representam {top_5_produtos_share:.2%} do faturamento."
        )

        return {
            "produtos_ativos": produtos_ativos,
            "produtos_classe_a": produtos_classe_a,
            "produtos_classe_b": produtos_classe_b,
            "produtos_classe_c": produtos_classe_c,
            "produtos_em_risco": produtos_em_risco,
            "faturamento_total": faturamento_total,
            "top_produto": top_produto,
            "top_produto_faturamento": top_produto_faturamento,
            "top_5_produtos_share": top_5_produtos_share,
            "headline": headline,
            "status": status
        }