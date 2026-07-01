class CustomerPerformance:

    def build(self, pedidos_df):

        ranking = (
            pedidos_df
            .groupby(["codigo_cliente", "Cliente"])
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                itens_vendidos=("codigo_item", "count"),
                mix_produtos=("prod_codigo", "nunique"),
                ultima_compra=("Data", "max")
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