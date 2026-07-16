import pandas as pd


class ProductPerformance:

    def build(self, pedidos_df: pd.DataFrame) -> pd.DataFrame:

        if pedidos_df.empty:
            return pd.DataFrame(columns=[
                "Empresa",
                "prod_codigo",
                "produto",
                "Classificacao",
                "unidade",
                "faturamento_total",
                "quantidade",
                "pedidos",
                "clientes",
                "ticket_medio"
            ])

        by_company = (
            pedidos_df
            .groupby(["Empresa", "prod_codigo", "produto", "Classificacao", "unidade"])
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                quantidade=("Quantidade", "sum"),
                pedidos=("numero_pedido", "nunique"),
                clientes=("codigo_cliente", "nunique")
            )
            .reset_index()
        )

        total = (
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

        total["Empresa"] = "TOTAL"

        ranking = pd.concat(
            [total, by_company],
            ignore_index=True
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