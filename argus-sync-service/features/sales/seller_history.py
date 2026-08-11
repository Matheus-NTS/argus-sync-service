from __future__ import annotations

import json

import pandas as pd

from features.sales.seller_arena import SellerArena
from features.sales.seller_identity import SellerIdentity
from features.sales.seller_performance import SellerPerformance
from features.sales.seller_pace import SellerPace
from features.sales.seller_scorecards import SellerScorecards


class SellerHistory:
    """
    Gera histórico diário e mensal por vendedor usando exclusivamente
    os pedidos comerciais já filtrados pelo SalesPipeline.

    O módulo não reaplica regras comerciais e não altera os cálculos
    oficiais de SellerPerformance, Arena ou Health Score.
    """

    DAILY_COLUMNS = [
        "sale_date",
        "seller_key",
        "Vendedor",
        "Empresa",
        "faturamento_total",
        "pedidos",
        "itens_vendidos",
        "clientes",
        "mix_produtos",
        "ticket_medio",
    ]

    MONTHLY_COLUMNS = [
        "month_start",
        "seller_key",
        "Vendedor",
        "Empresa",
        "faturamento_total",
        "meta",
        "supermeta",
        "hipermeta",
        "atingimento",
        "status_meta",
        "pedidos",
        "itens_vendidos",
        "clientes",
        "mix_produtos",
        "ticket_medio",
        "ranking_faturamento",
        "ranking_atingimento",
        "arena_position",
        "arena_level",
        "seller_health_score",
        "seller_health_status",
        "seller_scorecards",
    ]

    def __init__(self):
        self.identity = SellerIdentity()

    def build_daily(
        self,
        pedidos_df: pd.DataFrame,
    ) -> pd.DataFrame:

        if pedidos_df is None or pedidos_df.empty:
            return pd.DataFrame(
                columns=self.DAILY_COLUMNS
            )

        required_columns = [
            "Data",
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
            if column not in pedidos_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Não foi possível gerar SellerHistory diário. "
                "Colunas ausentes: "
                + ", ".join(missing_columns)
            )

        df = pedidos_df[
            required_columns
        ].copy()

        df["Data"] = pd.to_datetime(
            df["Data"],
            errors="coerce",
        )

        df["Valor_total_Unitario"] = pd.to_numeric(
            df["Valor_total_Unitario"],
            errors="coerce",
        ).fillna(0)

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

        df = df[
            df["Data"].notna()
            & df["seller_key"].ne("")
            & df["Empresa"].ne("")
        ].copy()

        if df.empty:
            return pd.DataFrame(
                columns=self.DAILY_COLUMNS
            )

        df["sale_date"] = df["Data"].dt.date

        by_company = self._aggregate_daily(
            dataframe=df,
            group_columns=[
                "sale_date",
                "seller_key",
                "Vendedor",
                "Empresa",
            ],
        )

        total = self._aggregate_daily(
            dataframe=df,
            group_columns=[
                "sale_date",
                "seller_key",
                "Vendedor",
            ],
            empresa_value="TOTAL",
        )

        result = pd.concat(
            [total, by_company],
            ignore_index=True,
            sort=False,
        )

        result = (
            result
            .sort_values(
                [
                    "sale_date",
                    "seller_key",
                    "Empresa",
                ],
                ascending=True,
            )
            .drop_duplicates(
                subset=[
                    "sale_date",
                    "seller_key",
                    "Empresa",
                ],
                keep="first",
            )
            .reset_index(drop=True)
        )

        return result[
            self.DAILY_COLUMNS
        ]

    def build_monthly(
        self,
        pedidos_df: pd.DataFrame,
        meta_df: pd.DataFrame | None = None,
        reference_date=None,
    ) -> pd.DataFrame:

        if pedidos_df is None or pedidos_df.empty:
            return pd.DataFrame(
                columns=self.MONTHLY_COLUMNS
            )

        if "Data" not in pedidos_df.columns:
            raise KeyError(
                "Não foi possível gerar SellerHistory mensal. "
                "Coluna ausente: Data"
            )

        base = pedidos_df.copy()

        base["Data"] = pd.to_datetime(
            base["Data"],
            errors="coerce",
        )

        base = base[
            base["Data"].notna()
        ].copy()

        if base.empty:
            return pd.DataFrame(
                columns=self.MONTHLY_COLUMNS
            )

        base["_month_start"] = (
            base["Data"]
            .dt.to_period("M")
            .dt.to_timestamp()
        )

        resolved_reference = pd.to_datetime(
            reference_date,
            errors="coerce",
        )

        if pd.isna(resolved_reference):
            resolved_reference = base["Data"].max()

        current_month_start = (
            resolved_reference
            .to_period("M")
            .to_timestamp()
        )

        frames = []

        for month_start, month_df in base.groupby(
            "_month_start",
            sort=True,
        ):
            is_current_month = (
                pd.Timestamp(month_start)
                == pd.Timestamp(current_month_start)
            )

            month_orders = month_df.drop(
                columns=["_month_start"],
                errors="ignore",
            ).copy()

            month_period_type = (
                "current_month"
                if is_current_month
                else "month_previous"
            )

            seller_df = SellerPerformance().build(
                pedidos_df=month_orders,
                meta_df=meta_df,
                period_type=month_period_type,
            )

            if is_current_month:
                seller_df = SellerPace(
                    reference_date=resolved_reference.date()
                ).build(
                    seller_df=seller_df,
                    period_type="current_month",
                )

            seller_df = SellerArena().build(
                seller_df=seller_df,
                period_type=month_period_type,
            )

            seller_df = SellerScorecards().build(
                seller_df=seller_df,
                period_type=month_period_type,
            )

            if seller_df.empty:
                continue

            total_rows = self._build_total_month_rows(
                seller_df=seller_df,
                month_start=month_start,
            )

            company_rows = self._build_company_month_rows(
                seller_df=seller_df,
                month_start=month_start,
            )

            frames.extend(
                [total_rows, company_rows]
            )

        if not frames:
            return pd.DataFrame(
                columns=self.MONTHLY_COLUMNS
            )

        result = pd.concat(
            frames,
            ignore_index=True,
            sort=False,
        )

        result = (
            result
            .sort_values(
                [
                    "month_start",
                    "seller_key",
                    "Empresa",
                ],
                ascending=True,
            )
            .drop_duplicates(
                subset=[
                    "month_start",
                    "seller_key",
                    "Empresa",
                ],
                keep="first",
            )
            .reset_index(drop=True)
        )

        return result[
            self.MONTHLY_COLUMNS
        ]

    @staticmethod
    def _aggregate_daily(
        dataframe: pd.DataFrame,
        group_columns: list[str],
        empresa_value: str | None = None,
    ) -> pd.DataFrame:

        result = (
            dataframe
            .groupby(
                group_columns,
                as_index=False,
                dropna=False,
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

        if empresa_value is not None:
            result["Empresa"] = empresa_value

        result["ticket_medio"] = (
            result["faturamento_total"]
            / result["pedidos"].replace(0, pd.NA)
        ).fillna(0)

        return result

    def _build_total_month_rows(
        self,
        seller_df: pd.DataFrame,
        month_start: pd.Timestamp,
    ) -> pd.DataFrame:

        rows = []

        for _, row in seller_df.iterrows():
            rows.append({
                "month_start": month_start.date(),
                "seller_key": row["seller_key"],
                "Vendedor": row["Vendedor"],
                "Empresa": "TOTAL",
                "faturamento_total": float(
                    row["faturamento_total"]
                ),
                "meta": float(
                    row.get("meta_mensal", 0)
                ),
                "supermeta": float(
                    row.get("supermeta", 0)
                ),
                "hipermeta": float(
                    row.get("hipermeta", 0)
                ),
                "atingimento": float(
                    row.get("atingimento", 0)
                ),
                "status_meta": row.get(
                    "status_meta",
                    "sem_meta",
                ),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(
                    row["itens_vendidos"]
                ),
                "clientes": int(row["clientes"]),
                "mix_produtos": int(
                    row["mix_produtos"]
                ),
                "ticket_medio": float(
                    row["ticket_medio"]
                ),
                "ranking_faturamento": self._optional_int(
                    row.get("ranking_faturamento")
                ),
                "ranking_atingimento": self._optional_int(
                    row.get("ranking_atingimento")
                ),
                "arena_position": self._optional_int(
                    row.get("arena_position")
                ),
                "arena_level": self._optional_text(
                    row.get("arena_level")
                ),
                "seller_health_score": self._optional_float(
                    row.get("seller_health_score")
                ),
                "seller_health_status": self._optional_text(
                    row.get("seller_health_status")
                ),
                "seller_scorecards": self._parse_json(
                    row.get("seller_scorecards")
                ),
            })

        return pd.DataFrame(rows)

    def _build_company_month_rows(
        self,
        seller_df: pd.DataFrame,
        month_start: pd.Timestamp,
    ) -> pd.DataFrame:

        rows = []

        for _, row in seller_df.iterrows():
            breakdown = row.get(
                "empresa_breakdown",
                [],
            )

            if not isinstance(breakdown, list):
                continue

            for company in breakdown:
                pedidos = int(
                    company.get("pedidos", 0)
                )

                faturamento = float(
                    company.get(
                        "faturamento_total",
                        0,
                    )
                )

                rows.append({
                    "month_start": month_start.date(),
                    "seller_key": row["seller_key"],
                    "Vendedor": row["Vendedor"],
                    "Empresa": company.get(
                        "empresa",
                        "",
                    ),
                    "faturamento_total": faturamento,
                    "meta": float(
                        company.get("meta", 0)
                    ),
                    "supermeta": float(
                        company.get("supermeta", 0)
                    ),
                    "hipermeta": float(
                        company.get("hipermeta", 0)
                    ),
                    "atingimento": float(
                        company.get("atingimento", 0)
                    ),
                    "status_meta": company.get(
                        "status_meta",
                        "sem_meta",
                    ),
                    "pedidos": pedidos,
                    "itens_vendidos": int(
                        company.get(
                            "itens_vendidos",
                            0,
                        )
                    ),
                    "clientes": int(
                        company.get("clientes", 0)
                    ),
                    "mix_produtos": int(
                        company.get(
                            "mix_produtos",
                            0,
                        )
                    ),
                    "ticket_medio": (
                        faturamento / pedidos
                        if pedidos > 0
                        else 0
                    ),
                    "ranking_faturamento": None,
                    "ranking_atingimento": None,
                    "arena_position": None,
                    "arena_level": None,
                    "seller_health_score": None,
                    "seller_health_status": None,
                    "seller_scorecards": None,
                })

        return pd.DataFrame(rows)

    @staticmethod
    def _parse_json(value):

        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if pd.isna(value):
            return None

        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _optional_float(value):

        if value is None or pd.isna(value):
            return None

        return float(value)

    @staticmethod
    def _optional_int(value):

        if value is None or pd.isna(value):
            return None

        return int(value)

    @staticmethod
    def _optional_text(value):

        if value is None or pd.isna(value):
            return None

        text = str(value).strip()

        return text if text else None