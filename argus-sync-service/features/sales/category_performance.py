import pandas as pd


class CategoryPerformance:

    def build(self, pedidos_df: pd.DataFrame) -> pd.DataFrame:

        if pedidos_df.empty:
            return pd.DataFrame(columns=[
                "Empresa",
                "Categoria",
                "faturamento_total",
                "pedidos",
                "itens_vendidos",
                "clientes",
                "produtos",
                "ticket_medio"
            ])

        by_company = (
            pedidos_df
            .groupby(["Empresa", "Classificacao"])
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                itens_vendidos=("codigo_item", "count"),
                clientes=("codigo_cliente", "nunique"),
                produtos=("prod_codigo", "nunique")
            )
            .reset_index()
        )

        total = (
            pedidos_df
            .groupby(["Classificacao"])
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                itens_vendidos=("codigo_item", "count"),
                clientes=("codigo_cliente", "nunique"),
                produtos=("prod_codigo", "nunique")
            )
            .reset_index()
        )

        total["Empresa"] = "TOTAL"

        ranking = pd.concat(
            [total, by_company],
            ignore_index=True
        )

        ranking = ranking.rename(
            columns={
                "Classificacao": "Categoria"
            }
        )

        ranking["ticket_medio"] = (
            ranking["faturamento_total"] /
            ranking["pedidos"].replace(0, pd.NA)
        ).fillna(0)

        ranking = ranking.sort_values(
            by=["Empresa", "faturamento_total"],
            ascending=[True, False]
        )

        return ranking