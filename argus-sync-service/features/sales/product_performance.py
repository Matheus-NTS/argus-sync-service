import pandas as pd


class ProductPerformance:

    EXCLUDED_PRODUCT_CODES = {
        "999999",
    }

    @classmethod
    def _filter_valid_products(
        cls,
        pedidos_df: pd.DataFrame,
    ) -> pd.DataFrame:

        if "prod_codigo" not in pedidos_df.columns:
            raise KeyError(
                "A coluna 'prod_codigo' não foi encontrada "
                "na base de pedidos."
            )

        product_codes = (
            pedidos_df["prod_codigo"]
            .astype(str)
            .str.strip()
        )

        valid_mask = ~product_codes.isin(
            cls.EXCLUDED_PRODUCT_CODES
        )

        filtered_df = pedidos_df[
            valid_mask
        ].copy()

        print(
            "Filtro da dimensão Produtos aplicado:"
        )
        print(
            f"  Registros recebidos: {len(pedidos_df):,}"
        )
        print(
            f"  Registros válidos: {len(filtered_df):,}"
        )
        print(
            f"  Códigos administrativos excluídos: "
            f"{len(pedidos_df) - len(filtered_df):,}"
        )

        return filtered_df

    def build(
        self,
        pedidos_df: pd.DataFrame,
    ) -> pd.DataFrame:

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
                "ticket_medio",
            ])

        produtos_df = self._filter_valid_products(
            pedidos_df
        )

        if produtos_df.empty:
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
                "ticket_medio",
            ])

        by_company = (
            produtos_df
            .groupby([
                "Empresa",
                "prod_codigo",
                "produto",
                "Classificacao",
                "unidade",
            ])
            .agg(
                faturamento_total=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                quantidade=(
                    "Quantidade",
                    "sum",
                ),
                pedidos=(
                    "numero_pedido",
                    "nunique",
                ),
                clientes=(
                    "codigo_cliente",
                    "nunique",
                ),
            )
            .reset_index()
        )

        total = (
            produtos_df
            .groupby([
                "prod_codigo",
                "produto",
                "Classificacao",
                "unidade",
            ])
            .agg(
                faturamento_total=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                quantidade=(
                    "Quantidade",
                    "sum",
                ),
                pedidos=(
                    "numero_pedido",
                    "nunique",
                ),
                clientes=(
                    "codigo_cliente",
                    "nunique",
                ),
            )
            .reset_index()
        )

        total["Empresa"] = "TOTAL"

        ranking = pd.concat(
            [
                total,
                by_company,
            ],
            ignore_index=True,
        )

        ranking["ticket_medio"] = (
            ranking["faturamento_total"]
            / ranking["pedidos"].replace(0, pd.NA)
        ).fillna(0)

        ranking = ranking.sort_values(
            by=[
                "Empresa",
                "faturamento_total",
            ],
            ascending=[
                True,
                False,
            ],
        )

        return ranking