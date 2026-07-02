class CategoryOverview:

    def build(self, category_df):

        categorias_ativas = len(category_df)

        faturamento_total = (
            float(category_df["faturamento_total"].sum())
            if categorias_ativas > 0
            else 0
        )

        top_categoria = None
        top_categoria_faturamento = 0

        produtos_total = (
            int(category_df["produtos"].sum())
            if categorias_ativas > 0
            else 0
        )

        clientes_total = (
            int(category_df["clientes"].sum())
            if categorias_ativas > 0
            else 0
        )

        if categorias_ativas > 0:
            top_row = category_df.sort_values(
                by="faturamento_total",
                ascending=False
            ).iloc[0]

            top_categoria = top_row["Categoria"]
            top_categoria_faturamento = float(top_row["faturamento_total"])

        if categorias_ativas <= 3:
            status = "attention"
        else:
            status = "healthy"

        headline = (
            f"O mix comercial possui {categorias_ativas} categorias ativas no mês. "
            f"A principal categoria é {top_categoria}, com "
            f"R$ {top_categoria_faturamento:,.2f} em faturamento."
        )

        return {
            "categorias_ativas": categorias_ativas,
            "faturamento_total": faturamento_total,
            "top_categoria": top_categoria,
            "top_categoria_faturamento": top_categoria_faturamento,
            "produtos_total": produtos_total,
            "clientes_total": clientes_total,
            "headline": headline,
            "status": status
        }