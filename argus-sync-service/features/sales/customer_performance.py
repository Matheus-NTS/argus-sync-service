import pandas as pd
from datetime import datetime


class CustomerPerformance:

    def build(self, pedidos_df: pd.DataFrame) -> pd.DataFrame:

        columns = [
            "Empresa", "codigo_cliente", "Cliente",
            "faturamento_total", "faturamento_90d", "faturamento_180d",
            "faturamento_90d_anterior", "variacao_faturamento_90d",
            "pedidos", "itens_vendidos", "mix_produtos", "ultima_compra",
            "dias_sem_compra", "ticket_medio", "produtos_comprados",
            "evolution_status", "fidelidade_score", "customer_tier",
            "cliente_status"
        ]

        if pedidos_df.empty:
            return pd.DataFrame(columns=columns)

        df = pedidos_df.copy()
        hoje = datetime.today().date()

        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df["Valor_total_Unitario"] = pd.to_numeric(df["Valor_total_Unitario"], errors="coerce").fillna(0)

        data_90 = pd.Timestamp(hoje) - pd.Timedelta(days=90)
        data_180 = pd.Timestamp(hoje) - pd.Timedelta(days=180)

        def build_group(base_df, group_cols, empresa_value=None):

            grouped = (
                base_df
                .groupby(group_cols)
                .agg(
                    faturamento_total=("Valor_total_Unitario", "sum"),
                    pedidos=("numero_pedido", "nunique"),
                    itens_vendidos=("codigo_item", "count"),
                    mix_produtos=("prod_codigo", "nunique"),
                    ultima_compra=("Data", "max")
                )
                .reset_index()
            )

            atual_90 = (
                base_df[base_df["Data"] >= data_90]
                .groupby(group_cols)
                .agg(faturamento_90d=("Valor_total_Unitario", "sum"))
                .reset_index()
            )

            anterior_90 = (
                base_df[(base_df["Data"] >= data_180) & (base_df["Data"] < data_90)]
                .groupby(group_cols)
                .agg(faturamento_90d_anterior=("Valor_total_Unitario", "sum"))
                .reset_index()
            )

            atual_180 = (
                base_df[base_df["Data"] >= data_180]
                .groupby(group_cols)
                .agg(faturamento_180d=("Valor_total_Unitario", "sum"))
                .reset_index()
            )

            produtos = (
                base_df
                .groupby(group_cols)["produto"]
                .apply(lambda x: ", ".join(x.dropna().astype(str).value_counts().head(8).index))
                .reset_index(name="produtos_comprados")
            )

            result = grouped.merge(atual_90, on=group_cols, how="left")
            result = result.merge(anterior_90, on=group_cols, how="left")
            result = result.merge(atual_180, on=group_cols, how="left")
            result = result.merge(produtos, on=group_cols, how="left")

            if empresa_value:
                result["Empresa"] = empresa_value

            return result

        by_company = build_group(
            df,
            ["Empresa", "codigo_cliente", "Cliente"]
        )

        total = build_group(
            df,
            ["codigo_cliente", "Cliente"],
            empresa_value="TOTAL"
        )

        ranking = pd.concat([total, by_company], ignore_index=True)

        for col in ["faturamento_90d", "faturamento_90d_anterior", "faturamento_180d"]:
            ranking[col] = ranking[col].fillna(0)

        ranking["ticket_medio"] = (
            ranking["faturamento_total"] /
            ranking["pedidos"].replace(0, pd.NA)
        ).fillna(0)

        ranking["dias_sem_compra"] = ranking["ultima_compra"].apply(
            lambda x: (pd.Timestamp(hoje) - x).days if pd.notnull(x) else None
        )

        ranking["variacao_faturamento_90d"] = ranking.apply(
            lambda row: (
                (row["faturamento_90d"] - row["faturamento_90d_anterior"]) /
                row["faturamento_90d_anterior"]
                if row["faturamento_90d_anterior"] > 0
                else 0
            ),
            axis=1
        )

        def evolution(row):
            if row["variacao_faturamento_90d"] >= 0.15:
                return "evolucao"
            if row["variacao_faturamento_90d"] <= -0.15:
                return "involucao"
            return "estavel"

        def status(row):
            dias = row["dias_sem_compra"]

            if dias is None:
                return "sem_historico"
            if dias > 120:
                return "inativo"
            if dias > 60 or row["variacao_faturamento_90d"] <= -0.30:
                return "risco"
            return "saudavel"

        ranking["evolution_status"] = ranking.apply(evolution, axis=1)
        ranking["cliente_status"] = ranking.apply(status, axis=1)

        ranking["faturamento_rank_pct"] = ranking.groupby("Empresa")["faturamento_total"].rank(pct=True)
        ranking["pedidos_rank_pct"] = ranking.groupby("Empresa")["pedidos"].rank(pct=True)
        ranking["mix_rank_pct"] = ranking.groupby("Empresa")["mix_produtos"].rank(pct=True)

        ranking["recency_score"] = ranking["dias_sem_compra"].apply(
            lambda d: 1 if d is not None and d <= 30 else
            0.75 if d is not None and d <= 60 else
            0.45 if d is not None and d <= 120 else
            0.15
        )

        ranking["fidelidade_score"] = (
            (ranking["faturamento_rank_pct"] * 40) +
            (ranking["pedidos_rank_pct"] * 25) +
            (ranking["mix_rank_pct"] * 20) +
            (ranking["recency_score"] * 15)
        ).round(2)

        def tier(score):
            if score >= 85:
                return "diamante"
            if score >= 70:
                return "ouro"
            if score >= 50:
                return "prata"
            return "bronze"

        ranking["customer_tier"] = ranking["fidelidade_score"].apply(tier)

        ranking = ranking.drop(
            columns=["faturamento_rank_pct", "pedidos_rank_pct", "mix_rank_pct", "recency_score"],
            errors="ignore"
        )

        ranking = ranking.sort_values(
            by=["Empresa", "fidelidade_score", "faturamento_total"],
            ascending=[True, False, False]
        )

        return ranking[columns]