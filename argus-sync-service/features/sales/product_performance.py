class ProductPerformance:

    def build(self, pedidos_df):

        ranking = (
            pedidos_df
            .groupby(["prod_codigo", "produto", "Classificacao", "unidade"])
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                quantidade=("Quantidade", "sum"),
                pedidos=("numero_pedido", "nunique"),
                clientes=("codigo_cliente", "nunique")
            )
            .reset_index()
        )

        ranking["ticket_medio"] = (
            ranking["faturamento_total"] / ranking["pedidos"]
        )

        ranking = ranking.sort_values(
            by="faturamento_total",
            ascending=False
        )

        return ranking