class CompanyPerformance:

    def build(self, pedidos_df):

        ranking = (
            pedidos_df
            .groupby("Empresa")
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                itens_vendidos=("codigo_item", "count"),
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