import pandas as pd


class CategoryPerformance:

    def build(self, pedidos_df: pd.DataFrame) -> pd.DataFrame:

        ranking = (
            pedidos_df
            .groupby("Classificacao")
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                itens_vendidos=("codigo_item", "count"),
                clientes=("codigo_cliente", "nunique"),
                produtos=("prod_codigo", "nunique")
            )
            .reset_index()
        )

        ranking["ticket_medio"] = (
            ranking["faturamento_total"] /
            ranking["pedidos"]
        )

        ranking = ranking.sort_values(
            by="faturamento_total",
            ascending=False
        )

        ranking = ranking.rename(
            columns={
                "Classificacao": "Categoria"
            }
        )

        return ranking