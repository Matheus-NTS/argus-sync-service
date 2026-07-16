from datetime import datetime, timedelta
import pandas as pd


class SalesHistoryPipeline:

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

    def run(self, pedidos):

        hoje = datetime.today().date()

        pedidos = pedidos.copy()
        pedidos["Data"] = pd.to_datetime(pedidos["Data"], errors="coerce")
        pedidos = pedidos[pedidos["Data"].notna()].copy()

        daily_records = self._build_daily(pedidos, hoje)
        weekly_records = self._build_weekly(pedidos, hoje)
        monthly_records = self._build_monthly(pedidos, hoje)

        self.supabase.replace_snapshot(
            "mart_sales_daily_history",
            {"reference_date": hoje.isoformat()},
            daily_records
        )

        self.supabase.replace_snapshot(
            "mart_sales_weekly_history",
            {"reference_date": hoje.isoformat()},
            weekly_records
        )

        self.supabase.replace_snapshot(
            "mart_sales_monthly_history",
            {"reference_date": hoje.isoformat()},
            monthly_records
        )

        return {
            "daily_history": len(daily_records),
            "weekly_history": len(weekly_records),
            "monthly_history": len(monthly_records)
        }

    def _aggregate(self, df, group_cols, reference_date):

        if df.empty:
            return []

        records = []

        grouped = (
            df
            .groupby(group_cols + ["Empresa"], dropna=False)
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                clientes=("codigo_cliente", "nunique"),
                skus=("prod_codigo", "nunique"),
                itens_vendidos=("codigo_item", "count")
            )
            .reset_index()
        )

        for _, row in grouped.iterrows():
            pedidos = int(row["pedidos"])
            faturamento = float(row["faturamento_total"])

            record = {
                "reference_date": reference_date.isoformat(),
                "empresa": row["Empresa"],
                "faturamento_total": round(faturamento, 2),
                "pedidos": pedidos,
                "clientes": int(row["clientes"]),
                "skus": int(row["skus"]),
                "itens_vendidos": float(row["itens_vendidos"]),
                "ticket_medio": round(faturamento / pedidos, 2) if pedidos else 0
            }

            for col in group_cols:
                value = row[col]
                if hasattr(value, "date"):
                    value = value.date()
                record[col] = value.isoformat()

            records.append(record)

        total_grouped = (
            df
            .groupby(group_cols, dropna=False)
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                clientes=("codigo_cliente", "nunique"),
                skus=("prod_codigo", "nunique"),
                itens_vendidos=("codigo_item", "count")
            )
            .reset_index()
        )

        for _, row in total_grouped.iterrows():
            pedidos = int(row["pedidos"])
            faturamento = float(row["faturamento_total"])

            record = {
                "reference_date": reference_date.isoformat(),
                "empresa": "TOTAL",
                "faturamento_total": round(faturamento, 2),
                "pedidos": pedidos,
                "clientes": int(row["clientes"]),
                "skus": int(row["skus"]),
                "itens_vendidos": float(row["itens_vendidos"]),
                "ticket_medio": round(faturamento / pedidos, 2) if pedidos else 0
            }

            for col in group_cols:
                value = row[col]
                if hasattr(value, "date"):
                    value = value.date()
                record[col] = value.isoformat()

            records.append(record)

        return records

    def _build_daily(self, pedidos, hoje):

        cutoff = hoje - timedelta(days=180)

        df = pedidos[pedidos["Data"].dt.date >= cutoff].copy()
        df["bucket_date"] = df["Data"].dt.date

        return self._aggregate(df, ["bucket_date"], hoje)

    def _build_weekly(self, pedidos, hoje):

        cutoff = hoje - timedelta(weeks=52)

        df = pedidos[pedidos["Data"].dt.date >= cutoff].copy()
        df["bucket_week"] = (
            df["Data"] - pd.to_timedelta(df["Data"].dt.weekday, unit="D")
        ).dt.date

        return self._aggregate(df, ["bucket_week"], hoje)

    def _build_monthly(self, pedidos, hoje):

        cutoff = hoje.replace(day=1) - pd.DateOffset(months=24)

        df = pedidos[pedidos["Data"] >= cutoff].copy()
        df["bucket_month"] = df["Data"].dt.to_period("M").dt.to_timestamp().dt.date

        return self._aggregate(df, ["bucket_month"], hoje)