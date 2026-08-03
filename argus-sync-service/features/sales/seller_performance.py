import pandas as pd

from features.sales.seller_identity import SellerIdentity


class SellerPerformance:

    GOAL_PERIODS = {
    "current_month",
    "month_current",
    "month_previous",
    "ytd",
    "ytd_previous",
}

    def __init__(self):

        self.identity = SellerIdentity()

    def build(
        self,
        pedidos_df: pd.DataFrame,
        meta_df: pd.DataFrame | None = None,
        period_type: str = "current_month",
    ) -> pd.DataFrame:

        columns = [
            "seller_key",
            "Vendedor",
            "faturamento_total",
            "pedidos",
            "itens_vendidos",
            "clientes",
            "mix_produtos",
            "ticket_medio",
            "empresa_breakdown",
            "meta_mensal",
            "supermeta",
            "hipermeta",
            "atingimento",
            "atingimento_supermeta",
            "atingimento_hipermeta",
            "gap_meta",
            "gap_supermeta",
            "gap_hipermeta",
            "meta_valida",
            "meta_batida",
            "arena_eligible",
            "status_meta",
            "ranking_faturamento",
            "ranking_atingimento",
        ]

        if pedidos_df is None or pedidos_df.empty:
            return pd.DataFrame(columns=columns)

        df = pedidos_df.copy()

        required_columns = [
            "Vendedor",
            "Empresa",
            "Valor_total_Unitario",
            "numero_pedido",
            "codigo_item",
            "codigo_cliente",
            "prod_codigo",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Não foi possível gerar SellerPerformance. "
                "Colunas ausentes: "
                + ", ".join(missing_columns)
            )

        df["Vendedor"] = (
            df["Vendedor"]
            .apply(self.identity.normalize_name)
        )

        df["seller_key"] = (
            df["Vendedor"]
            .apply(self.identity.seller_key)
        )

        df["Empresa"] = (
            df["Empresa"]
            .apply(self.identity.normalize_company)
        )

        df["Valor_total_Unitario"] = pd.to_numeric(
            df["Valor_total_Unitario"],
            errors="coerce",
        ).fillna(0)

        df = df[
            df["seller_key"].ne("")
            & df["Empresa"].ne("")
        ].copy()

        ranking = (
            df
            .groupby(
                [
                    "seller_key",
                    "Vendedor",
                ],
                as_index=False,
            )
            .agg(
                faturamento_total=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                pedidos=(
                    "numero_pedido",
                    "nunique",
                ),
                itens_vendidos=(
                    "codigo_item",
                    "count",
                ),
                clientes=(
                    "codigo_cliente",
                    "nunique",
                ),
                mix_produtos=(
                    "prod_codigo",
                    "nunique",
                ),
            )
        )

        ranking["ticket_medio"] = (
            ranking["faturamento_total"]
            / ranking["pedidos"].replace(0, pd.NA)
        ).fillna(0)

        company_performance = (
            df
            .groupby(
                [
                    "seller_key",
                    "Empresa",
                ],
                as_index=False,
            )
            .agg(
                faturamento_total=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                pedidos=(
                    "numero_pedido",
                    "nunique",
                ),
                itens_vendidos=(
                    "codigo_item",
                    "count",
                ),
                clientes=(
                    "codigo_cliente",
                    "nunique",
                ),
                mix_produtos=(
                    "prod_codigo",
                    "nunique",
                ),
            )
        )

        prepared_meta = self._prepare_meta(
            meta_df=meta_df,
            pedidos_df=df,
            period_type=period_type,
        )

        ranking = self._apply_consolidated_goals(
            ranking=ranking,
            prepared_meta=prepared_meta,
        )

        company_performance = self._apply_company_goals(
            company_performance=company_performance,
            prepared_meta=prepared_meta,
        )

        breakdown_map = self._build_company_breakdown(
            company_performance
        )

        ranking["empresa_breakdown"] = (
            ranking["seller_key"]
            .map(breakdown_map)
            .apply(
                lambda value:
                value
                if isinstance(value, list)
                else []
            )
        )

        ranking["supermeta"] = (
            ranking["meta_mensal"] * 1.24
        )

        ranking["hipermeta"] = (
            ranking["meta_mensal"] * 1.37
        )

        ranking["meta_valida"] = (
            ranking["meta_mensal"] > 0
        )

        ranking["arena_eligible"] = (
            ranking["meta_valida"]
        )

        ranking["atingimento"] = ranking.apply(
            lambda row: (
                row["faturamento_total"]
                / row["meta_mensal"]
            )
            if row["meta_mensal"] > 0
            else 0,
            axis=1,
        )

        ranking["atingimento_supermeta"] = ranking.apply(
            lambda row: (
                row["faturamento_total"]
                / row["supermeta"]
            )
            if row["supermeta"] > 0
            else 0,
            axis=1,
        )

        ranking["atingimento_hipermeta"] = ranking.apply(
            lambda row: (
                row["faturamento_total"]
                / row["hipermeta"]
            )
            if row["hipermeta"] > 0
            else 0,
            axis=1,
        )

        ranking["gap_meta"] = (
            ranking["meta_mensal"]
            - ranking["faturamento_total"]
        ).clip(lower=0)

        ranking["gap_supermeta"] = (
            ranking["supermeta"]
            - ranking["faturamento_total"]
        ).clip(lower=0)

        ranking["gap_hipermeta"] = (
            ranking["hipermeta"]
            - ranking["faturamento_total"]
        ).clip(lower=0)

        ranking["meta_batida"] = (
            ranking["meta_valida"]
            & (
                ranking["faturamento_total"]
                >= ranking["meta_mensal"]
            )
        )

        ranking["status_meta"] = "sem_meta"

        ranking.loc[
            ranking["meta_valida"],
            "status_meta",
        ] = "abaixo_meta"

        ranking.loc[
            ranking["meta_batida"],
            "status_meta",
        ] = "meta"

        ranking.loc[
            ranking["meta_valida"]
            & (
                ranking["faturamento_total"]
                >= ranking["supermeta"]
            ),
            "status_meta",
        ] = "supermeta"

        ranking.loc[
            ranking["meta_valida"]
            & (
                ranking["faturamento_total"]
                >= ranking["hipermeta"]
            ),
            "status_meta",
        ] = "hipermeta"

        ranking["ranking_faturamento"] = (
            ranking["faturamento_total"]
            .rank(
                method="dense",
                ascending=False,
            )
            .astype(int)
        )

        ranking["ranking_atingimento"] = pd.NA

        eligible_mask = ranking["arena_eligible"]

        if eligible_mask.any():
            ranking.loc[
                eligible_mask,
                "ranking_atingimento",
            ] = (
                ranking.loc[
                    eligible_mask,
                    "atingimento",
                ]
                .rank(
                    method="dense",
                    ascending=False,
                )
                .astype(int)
            )

        numeric_columns = [
            "faturamento_total",
            "ticket_medio",
            "meta_mensal",
            "supermeta",
            "hipermeta",
            "atingimento",
            "atingimento_supermeta",
            "atingimento_hipermeta",
            "gap_meta",
            "gap_supermeta",
            "gap_hipermeta",
        ]

        for column in numeric_columns:
            ranking[column] = pd.to_numeric(
                ranking[column],
                errors="coerce",
            ).fillna(0)

        ranking = (
            ranking
            .sort_values(
                [
                    "faturamento_total",
                    "Vendedor",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .reset_index(drop=True)
        )

        return ranking[columns]

    def _prepare_meta(
        self,
        meta_df: pd.DataFrame | None,
        pedidos_df: pd.DataFrame,
        period_type: str,
    ) -> pd.DataFrame:

        columns = [
            "seller_key",
            "Vendedor",
            "Empresa",
            "ano",
            "mes",
            "meta",
        ]

        if (
            meta_df is None
            or meta_df.empty
            or period_type not in self.GOAL_PERIODS
        ):
            return pd.DataFrame(columns=columns)

        meta = meta_df.copy()

        normalized_columns = {
            str(column).strip().lower(): column
            for column in meta.columns
        }

        vendedor_column = normalized_columns.get(
            "vendedor"
        )

        empresa_column = normalized_columns.get(
            "empresa"
        )

        valor_column = normalized_columns.get(
            "valor"
        )

        ano_column = normalized_columns.get(
            "ano"
        )

        mes_column = normalized_columns.get(
            "mes"
        )

        required = {
            "vendedor": vendedor_column,
            "empresa": empresa_column,
            "valor": valor_column,
            "ano": ano_column,
            "mes": mes_column,
        }

        missing = [
            name
            for name, column
            in required.items()
            if column is None
        ]

        if missing:
            raise KeyError(
                "Não foi possível preparar as metas dos vendedores. "
                "Colunas ausentes na agrc_meta_vendedor: "
                + ", ".join(missing)
            )

        meta = meta[
            [
                vendedor_column,
                empresa_column,
                valor_column,
                ano_column,
                mes_column,
            ]
        ].copy()

        meta = meta.rename(
            columns={
                vendedor_column: "Vendedor",
                empresa_column: "Empresa",
                valor_column: "meta",
                ano_column: "ano",
                mes_column: "mes",
            }
        )

        meta["Vendedor"] = (
            meta["Vendedor"]
            .apply(self.identity.normalize_name)
        )

        meta["seller_key"] = (
            meta["Vendedor"]
            .apply(self.identity.seller_key)
        )

        meta["Empresa"] = (
            meta["Empresa"]
            .apply(self.identity.normalize_company)
        )

        meta["ano"] = pd.to_numeric(
            meta["ano"],
            errors="coerce",
        )

        meta["mes"] = pd.to_numeric(
            meta["mes"],
            errors="coerce",
        )

        meta["meta"] = pd.to_numeric(
            meta["meta"],
            errors="coerce",
        ).fillna(0)

        meta = meta[
            meta["seller_key"].ne("")
            & meta["Empresa"].ne("")
            & meta["ano"].notna()
            & meta["mes"].notna()
        ].copy()

        if "Data" not in pedidos_df.columns:
            return pd.DataFrame(columns=columns)

        dates = pd.to_datetime(
            pedidos_df["Data"],
            errors="coerce",
        ).dropna()

        if dates.empty:
            return pd.DataFrame(columns=columns)

        first_date = dates.min()
        last_date = dates.max()

        first_period_key = (
            int(first_date.year) * 100
            + int(first_date.month)
        )

        last_period_key = (
            int(last_date.year) * 100
            + int(last_date.month)
        )

        meta["_period_key"] = (
            meta["ano"].astype(int) * 100
            + meta["mes"].astype(int)
        )

        meta = meta[
            (meta["_period_key"] >= first_period_key)
            & (meta["_period_key"] <= last_period_key)
        ].copy()

        meta = (
            meta
            .groupby(
                [
                    "seller_key",
                    "Vendedor",
                    "Empresa",
                    "ano",
                    "mes",
                ],
                as_index=False,
            )
            .agg(
                meta=(
                    "meta",
                    "sum",
                )
            )
        )

        return meta[columns]

    @staticmethod
    def _apply_consolidated_goals(
        ranking: pd.DataFrame,
        prepared_meta: pd.DataFrame,
    ) -> pd.DataFrame:

        result = ranking.copy()

        result["meta_mensal"] = 0.0

        if prepared_meta.empty:
            return result

        consolidated = (
            prepared_meta
            .groupby(
                "seller_key",
                as_index=False,
            )
            .agg(
                meta_mensal=(
                    "meta",
                    "sum",
                )
            )
        )

        result = result.drop(
            columns=["meta_mensal"],
            errors="ignore",
        )

        result = result.merge(
            consolidated,
            on="seller_key",
            how="left",
        )

        result["meta_mensal"] = pd.to_numeric(
            result["meta_mensal"],
            errors="coerce",
        ).fillna(0)

        return result

    @staticmethod
    def _apply_company_goals(
        company_performance: pd.DataFrame,
        prepared_meta: pd.DataFrame,
    ) -> pd.DataFrame:

        result = company_performance.copy()

        result["meta"] = 0.0

        if prepared_meta.empty:
            result["supermeta"] = 0.0
            result["hipermeta"] = 0.0
            result["atingimento"] = 0.0
            result["status_meta"] = "sem_meta"
            return result

        company_goals = (
            prepared_meta
            .groupby(
                [
                    "seller_key",
                    "Empresa",
                ],
                as_index=False,
            )
            .agg(
                meta=(
                    "meta",
                    "sum",
                )
            )
        )

        result = result.drop(
            columns=["meta"],
            errors="ignore",
        )

        result = result.merge(
            company_goals,
            on=[
                "seller_key",
                "Empresa",
            ],
            how="left",
        )

        result["meta"] = pd.to_numeric(
            result["meta"],
            errors="coerce",
        ).fillna(0)

        result["supermeta"] = (
            result["meta"] * 1.24
        )

        result["hipermeta"] = (
            result["meta"] * 1.37
        )

        result["atingimento"] = result.apply(
            lambda row: (
                row["faturamento_total"]
                / row["meta"]
            )
            if row["meta"] > 0
            else 0,
            axis=1,
        )

        result["status_meta"] = "sem_meta"

        result.loc[
            result["meta"] > 0,
            "status_meta",
        ] = "abaixo_meta"

        result.loc[
            (result["meta"] > 0)
            & (
                result["faturamento_total"]
                >= result["meta"]
            ),
            "status_meta",
        ] = "meta"

        result.loc[
            (result["meta"] > 0)
            & (
                result["faturamento_total"]
                >= result["supermeta"]
            ),
            "status_meta",
        ] = "supermeta"

        result.loc[
            (result["meta"] > 0)
            & (
                result["faturamento_total"]
                >= result["hipermeta"]
            ),
            "status_meta",
        ] = "hipermeta"

        return result

    @staticmethod
    def _build_company_breakdown(
        company_performance: pd.DataFrame,
    ) -> dict[str, list[dict]]:

        breakdown = {}

        for seller_key, group in company_performance.groupby(
            "seller_key"
        ):

            companies = []

            group = group.sort_values(
                "faturamento_total",
                ascending=False,
            )

            for _, row in group.iterrows():

                companies.append({
                    "empresa": row["Empresa"],
                    "faturamento_total": round(
                        float(row["faturamento_total"]),
                        2,
                    ),
                    "pedidos": int(
                        row["pedidos"]
                    ),
                    "itens_vendidos": int(
                        row["itens_vendidos"]
                    ),
                    "clientes": int(
                        row["clientes"]
                    ),
                    "mix_produtos": int(
                        row["mix_produtos"]
                    ),
                    "meta": round(
                        float(row.get("meta", 0)),
                        2,
                    ),
                    "supermeta": round(
                        float(row.get("supermeta", 0)),
                        2,
                    ),
                    "hipermeta": round(
                        float(row.get("hipermeta", 0)),
                        2,
                    ),
                    "atingimento": round(
                        float(row.get("atingimento", 0)),
                        6,
                    ),
                    "status_meta": row.get(
                        "status_meta",
                        "sem_meta",
                    ),
                })

            breakdown[seller_key] = companies

        return breakdown