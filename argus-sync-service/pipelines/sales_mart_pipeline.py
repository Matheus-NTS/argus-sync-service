from datetime import datetime
from time import perf_counter
import pandas as pd
import json

from features.sales.seller_performance import SellerPerformance
from features.sales.company_performance import CompanyPerformance
from features.sales.product_performance import ProductPerformance
from features.sales.customer_performance import CustomerPerformance
from features.sales.category_performance import CategoryPerformance
from features.sales.seller_pace import SellerPace
from features.sales.seller_arena import SellerArena
from features.sales.seller_scorecards import SellerScorecards
from features.sales.seller_benchmarks import SellerBenchmarks
from features.sales.seller_insights import SellerInsights
from features.sales.seller_history import SellerHistory
from features.sales.seller_timeline import SellerTimeline


class SalesMartPipeline:

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

    def run(
        self,
        pedidos,
        meta_df=None,
        period_type="current_month"
    ):

        hoje = datetime.today()

        filters = {
            "reference_date": hoje.date().isoformat(),
            "period_type": period_type
        }

        seller_df = SellerPerformance().build(
            pedidos_df=pedidos,
            meta_df=meta_df,
            period_type=period_type,
        )

        seller_df = SellerPace(
            reference_date=hoje.date()
        ).build(
            seller_df=seller_df,
            period_type=period_type,
        )

        seller_df = SellerArena().build(
            seller_df=seller_df,
            period_type=period_type,
        )

        seller_df = SellerScorecards().build(
            seller_df=seller_df,
            period_type=period_type,
        )

        seller_df = SellerBenchmarks().build(
            seller_df=seller_df,
            period_type=period_type,
        )

        seller_df = SellerInsights().build(
            seller_df=seller_df,
            period_type=period_type,
        )

        company_df = CompanyPerformance().build(pedidos)

        product_df_all = self._normalize_products(ProductPerformance().build(pedidos))
        customer_df_all = self._normalize_customers(CustomerPerformance().build(pedidos))
        category_df_all = self._normalize_categories(CategoryPerformance().build(pedidos))

        self._save_sellers(seller_df, filters)

        commercial_seller_records = (
            self._save_commercial_sellers(
                seller_df,
                filters
            )
        )
        self._save_companies(company_df, filters)
        self._save_products(product_df_all, filters)
        self._save_customers(customer_df_all, filters)
        self._save_categories(category_df_all, filters)

        customer_daily_records = 0
        product_daily_records = 0
        category_daily_records = 0
        seller_daily_records = 0
        seller_monthly_records = 0
        seller_timeline_records = 0

        if period_type == "historico":
            historical_timings = {}

            started_at = perf_counter()
            customer_daily_df = self._build_customer_daily(pedidos)
            historical_timings["customer_daily_build"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            customer_daily_records = self._save_customer_daily(
                customer_daily_df,
                reference_date=filters["reference_date"]
            )
            historical_timings["customer_daily_save"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            product_daily_df = self._build_product_daily(pedidos)
            historical_timings["product_daily_build"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            product_daily_records = self._save_product_daily(
                product_daily_df,
                reference_date=filters["reference_date"]
            )
            historical_timings["product_daily_save"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            category_daily_df = self._build_category_daily(pedidos)
            historical_timings["category_daily_build"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            category_daily_records = self._save_category_daily(
                category_daily_df,
                reference_date=filters["reference_date"]
            )
            historical_timings["category_daily_save"] = (
                perf_counter() - started_at
            )

            seller_history = SellerHistory()

            started_at = perf_counter()
            seller_daily_df = seller_history.build_daily(
                pedidos_df=pedidos
            )
            historical_timings["seller_daily_build"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            seller_daily_records = self._save_seller_daily(
                seller_daily_df=seller_daily_df,
                reference_date=filters["reference_date"]
            )
            historical_timings["seller_daily_save"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            seller_monthly_df = seller_history.build_monthly(
                pedidos_df=pedidos,
                meta_df=meta_df,
                reference_date=hoje.date()
            )
            historical_timings["seller_monthly_build"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            seller_monthly_records = self._save_seller_monthly(
                seller_monthly_df=seller_monthly_df,
                reference_date=filters["reference_date"]
            )
            historical_timings["seller_monthly_save"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            seller_timeline_df = SellerTimeline().build(
                monthly_df=seller_monthly_df,
                reference_date=hoje.date(),
                include_current_month=False
            )
            historical_timings["seller_timeline_build"] = (
                perf_counter() - started_at
            )

            started_at = perf_counter()
            seller_timeline_records = self._save_seller_timeline(
                seller_timeline_df=seller_timeline_df,
                reference_date=filters["reference_date"]
            )
            historical_timings["seller_timeline_save"] = (
                perf_counter() - started_at
            )

            print()
            print("=" * 60)
            print("SALES MART HISTORICO - BUILD X SAVE")
            print("=" * 60)

            for label, build_key, save_key in [
                (
                    "Customer daily",
                    "customer_daily_build",
                    "customer_daily_save",
                ),
                (
                    "Product daily",
                    "product_daily_build",
                    "product_daily_save",
                ),
                (
                    "Category daily",
                    "category_daily_build",
                    "category_daily_save",
                ),
                (
                    "Seller daily",
                    "seller_daily_build",
                    "seller_daily_save",
                ),
                (
                    "Seller monthly",
                    "seller_monthly_build",
                    "seller_monthly_save",
                ),
                (
                    "Seller timeline",
                    "seller_timeline_build",
                    "seller_timeline_save",
                ),
            ]:
                build_elapsed = historical_timings[build_key]
                save_elapsed = historical_timings[save_key]
                print(
                    f"{label:<18} "
                    f"build {build_elapsed:7.2f}s | "
                    f"save {save_elapsed:7.2f}s | "
                    f"total {build_elapsed + save_elapsed:7.2f}s"
                )

            historical_total = sum(
                historical_timings.values()
            )

            print("-" * 60)
            print(
                f"Historico medido: "
                f"{historical_total:.2f}s "
                f"({historical_total / 60:.2f} min)"
            )

        product_df_total = product_df_all[product_df_all["Empresa"] == "TOTAL"].copy()
        customer_df_total = customer_df_all[customer_df_all["Empresa"] == "TOTAL"].copy()
        category_df_total = category_df_all[category_df_all["Empresa"] == "TOTAL"].copy()

        return {
            "seller_df": seller_df,
            "commercial_seller_records": commercial_seller_records,
            "company_df": company_df,
            "product_df": product_df_total,
            "customer_df": customer_df_total,
            "category_df": category_df_total,
            "product_df_all": product_df_all,
            "customer_df_all": customer_df_all,
            "category_df_all": category_df_all,
            "customer_daily_records": customer_daily_records,
            "product_daily_records": product_daily_records,
            "category_daily_records": category_daily_records,
            "seller_daily_records": seller_daily_records,
            "seller_monthly_records": seller_monthly_records,
            "seller_timeline_records": seller_timeline_records
        }


    @staticmethod
    def _seller_daily_key(record):
        return (
            str(record.get("reference_date") or ""),
            str(record.get("sale_date") or ""),
            str(record.get("seller_key") or ""),
            str(record.get("empresa") or "")
        )

    @staticmethod
    def _seller_daily_comparable(record):
        def optional_float(value, decimals):
            if value is None:
                return None
            return round(float(value), decimals)

        def optional_int(value):
            if value is None:
                return None
            return int(value)

        def optional_text(value):
            if value is None:
                return None
            return str(value)

        return {
            "reference_date": str(record.get("reference_date") or ""),
            "sale_date": str(record.get("sale_date") or ""),
            "seller_key": str(record.get("seller_key") or ""),
            "empresa": str(record.get("empresa") or ""),
            "vendedor": optional_text(record.get("vendedor")),
            "faturamento_total": optional_float(
                record.get("faturamento_total"),
                2
            ),
            "pedidos": optional_int(record.get("pedidos")),
            "itens_vendidos": optional_int(
                record.get("itens_vendidos")
            ),
            "clientes": optional_int(record.get("clientes")),
            "mix_produtos": optional_int(
                record.get("mix_produtos")
            ),
            "ticket_medio": optional_float(
                record.get("ticket_medio"),
                2
            )
        }

    def _sync_seller_daily_diff(
        self,
        records,
        reference_date
    ):
        started_at = perf_counter()

        current_rows = self.supabase.select_rows_paginated(
            "mart_commercial_seller_daily",
            columns=(
                "id,reference_date,sale_date,seller_key,"
                "vendedor,empresa,faturamento_total,pedidos,"
                "itens_vendidos,clientes,mix_produtos,ticket_medio"
            ),
            filters={"reference_date": reference_date},
            order_by="id",
            page_size=1000,
        )

        generated_by_key = {}
        duplicate_generated_keys = 0

        for record in records:
            key = self._seller_daily_key(record)

            if key in generated_by_key:
                duplicate_generated_keys += 1

            generated_by_key[key] = record

        current_by_key = {}
        duplicate_current_keys = 0

        for record in current_rows:
            key = self._seller_daily_key(record)

            if key in current_by_key:
                duplicate_current_keys += 1

            current_by_key[key] = record

        if duplicate_generated_keys or duplicate_current_keys:
            raise RuntimeError(
                "Seller Daily incremental abortado: "
                "foram encontradas chaves duplicadas."
            )

        generated_keys = set(generated_by_key)
        current_keys = set(current_by_key)

        new_keys = generated_keys - current_keys
        removed_keys = current_keys - generated_keys
        common_keys = generated_keys & current_keys

        changed_keys = {
            key
            for key in common_keys
            if self._seller_daily_comparable(
                generated_by_key[key]
            )
            != self._seller_daily_comparable(
                current_by_key[key]
            )
        }

        unchanged_count = len(common_keys) - len(changed_keys)

        upsert_records = [
            generated_by_key[key]
            for key in (
                sorted(new_keys)
                + sorted(changed_keys)
            )
        ]

        removed_ids = [
            current_by_key[key]["id"]
            for key in sorted(removed_keys)
            if current_by_key[key].get("id") is not None
        ]

        if len(removed_ids) != len(removed_keys):
            raise RuntimeError(
                "Seller Daily incremental abortado: "
                "nem todos os removidos possuem id válido."
            )

        compare_elapsed = perf_counter() - started_at
        write_started_at = perf_counter()

        self.supabase.upsert_batches(
            table_name="mart_commercial_seller_daily",
            data=upsert_records,
            conflict_columns=(
                "reference_date,sale_date,seller_key,empresa"
            ),
            batch_size=500,
        )

        self.supabase.delete_ids_batches(
            table_name="mart_commercial_seller_daily",
            ids=removed_ids,
            id_column="id",
            batch_size=250,
        )

        write_elapsed = perf_counter() - write_started_at
        total_elapsed = perf_counter() - started_at

        print()
        print("=" * 60)
        print("SELLER DAILY - SYNC DIFERENCIAL")
        print("=" * 60)
        print(f"Snapshot anterior:   {len(current_rows):,}")
        print(f"Gerado agora:        {len(records):,}")
        print(f"Iguais:              {unchanged_count:,}")
        print(f"Novos:               {len(new_keys):,}")
        print(f"Alterados:           {len(changed_keys):,}")
        print(f"Removidos:           {len(removed_keys):,}")
        print(f"Upserts executados:  {len(upsert_records):,}")
        print(f"Deletes executados:  {len(removed_ids):,}")
        print(f"Comparação/leitura:  {compare_elapsed:.2f}s")
        print(f"Escrita diferencial: {write_elapsed:.2f}s")
        print(
            f"Tempo total sync:    "
            f"{total_elapsed:.2f}s "
            f"({total_elapsed / 60:.2f} min)"
        )
        print("=" * 60)

        return len(records)

    def _save_seller_daily(
        self,
        seller_daily_df,
        reference_date
    ):

        filters = {
            "reference_date": reference_date
        }

        records = []

        if (
            seller_daily_df is not None
            and not seller_daily_df.empty
        ):
            for _, row in seller_daily_df.iterrows():

                sale_date = pd.to_datetime(
                    row["sale_date"],
                    errors="coerce"
                )

                if pd.isna(sale_date):
                    continue

                records.append({
                    "reference_date": reference_date,
                    "sale_date": sale_date.date().isoformat(),
                    "seller_key": row["seller_key"],
                    "vendedor": row["Vendedor"],
                    "empresa": row["Empresa"],
                    "faturamento_total": round(
                        float(row["faturamento_total"]),
                        2
                    ),
                    "pedidos": int(row["pedidos"]),
                    "itens_vendidos": int(
                        row["itens_vendidos"]
                    ),
                    "clientes": int(row["clientes"]),
                    "mix_produtos": int(
                        row["mix_produtos"]
                    ),
                    "ticket_medio": round(
                        float(row["ticket_medio"]),
                        2
                    )
                })

        print(
            "  Publicando vendedores diÃ¡rios: "
            f"{len(records):,} registros"
        )

        return self._sync_seller_daily_diff(
            records=records,
            reference_date=reference_date
        )

    def _save_seller_monthly(
        self,
        seller_monthly_df,
        reference_date
    ):

        filters = {
            "reference_date": reference_date
        }

        records = []

        if (
            seller_monthly_df is not None
            and not seller_monthly_df.empty
        ):
            for _, row in seller_monthly_df.iterrows():

                month_start = pd.to_datetime(
                    row["month_start"],
                    errors="coerce"
                )

                if pd.isna(month_start):
                    continue

                scorecards = row.get(
                    "seller_scorecards"
                )

                if (
                    scorecards is not None
                    and not isinstance(
                        scorecards,
                        dict
                    )
                ):
                    try:
                        scorecards = json.loads(
                            scorecards
                        )
                    except (
                        TypeError,
                        json.JSONDecodeError
                    ):
                        scorecards = None

                records.append({
                    "reference_date": reference_date,
                    "month_start": (
                        month_start.date().isoformat()
                    ),
                    "seller_key": row["seller_key"],
                    "vendedor": row["Vendedor"],
                    "empresa": row["Empresa"],
                    "faturamento_total": round(
                        float(row["faturamento_total"]),
                        2
                    ),
                    "meta": round(
                        float(row["meta"]),
                        2
                    ),
                    "supermeta": round(
                        float(row["supermeta"]),
                        2
                    ),
                    "hipermeta": round(
                        float(row["hipermeta"]),
                        2
                    ),
                    "atingimento": round(
                        float(row["atingimento"]),
                        6
                    ),
                    "status_meta": row["status_meta"],
                    "pedidos": int(row["pedidos"]),
                    "itens_vendidos": int(
                        row["itens_vendidos"]
                    ),
                    "clientes": int(row["clientes"]),
                    "mix_produtos": int(
                        row["mix_produtos"]
                    ),
                    "ticket_medio": round(
                        float(row["ticket_medio"]),
                        2
                    ),
                    "ranking_faturamento": (
                        None
                        if pd.isna(
                            row.get(
                                "ranking_faturamento"
                            )
                        )
                        else int(
                            row.get(
                                "ranking_faturamento"
                            )
                        )
                    ),
                    "ranking_atingimento": (
                        None
                        if pd.isna(
                            row.get(
                                "ranking_atingimento"
                            )
                        )
                        else int(
                            row.get(
                                "ranking_atingimento"
                            )
                        )
                    ),
                    "arena_position": (
                        None
                        if pd.isna(
                            row.get("arena_position")
                        )
                        else int(
                            row.get("arena_position")
                        )
                    ),
                    "arena_level": (
                        None
                        if pd.isna(
                            row.get("arena_level")
                        )
                        else str(
                            row.get("arena_level")
                        )
                    ),
                    "seller_health_score": (
                        None
                        if pd.isna(
                            row.get(
                                "seller_health_score"
                            )
                        )
                        else round(
                            float(
                                row.get(
                                    "seller_health_score"
                                )
                            ),
                            2
                        )
                    ),
                    "seller_health_status": (
                        None
                        if pd.isna(
                            row.get(
                                "seller_health_status"
                            )
                        )
                        else str(
                            row.get(
                                "seller_health_status"
                            )
                        )
                    ),
                    "seller_scorecards": scorecards
                })

        print(
            "  Publicando vendedores mensais: "
            f"{len(records):,} registros"
        )

        self.supabase.replace_snapshot_batches(
            "mart_commercial_seller_monthly",
            filters,
            records,
            batch_size=500
        )

        return len(records)

    def _save_seller_timeline(
        self,
        seller_timeline_df,
        reference_date
    ):

        filters = {
            "reference_date": reference_date
        }

        records = []

        if (
            seller_timeline_df is not None
            and not seller_timeline_df.empty
        ):
            for _, row in seller_timeline_df.iterrows():

                event_date = pd.to_datetime(
                    row["event_date"],
                    errors="coerce"
                )

                if pd.isna(event_date):
                    continue

                metadata = row.get("metadata")

                if (
                    metadata is not None
                    and not isinstance(
                        metadata,
                        dict
                    )
                ):
                    try:
                        metadata = json.loads(
                            metadata
                        )
                    except (
                        TypeError,
                        json.JSONDecodeError
                    ):
                        metadata = None

                records.append({
                    "reference_date": reference_date,
                    "event_date": (
                        event_date.date().isoformat()
                    ),
                    "seller_key": row["seller_key"],
                    "vendedor": row["Vendedor"],
                    "event_type": row["event_type"],
                    "severity": row["severity"],
                    "title": row["title"],
                    "description": row["description"],
                    "metadata": metadata
                })

        print(
            "  Publicando timeline de vendedores: "
            f"{len(records):,} registros"
        )

        self.supabase.replace_snapshot_batches(
            "mart_commercial_seller_timeline",
            filters,
            records,
            batch_size=500
        )

        return len(records)

    def _normalize_products(self, product_df):

        if product_df is None or product_df.empty:
            return product_df

        df = product_df.copy()

        return (
            df.groupby(["Empresa", "prod_codigo"], as_index=False)
            .agg({
                "produto": "first",
                "Classificacao": "first",
                "unidade": "first",
                "faturamento_total": "sum",
                "quantidade": "sum",
                "pedidos": "sum",
                "clientes": "sum",
                "ticket_medio": "mean"
            })
        )

    def _normalize_customers(self, customer_df):

        if customer_df is None or customer_df.empty:
            return customer_df

        df = customer_df.copy()

        agg = {
            "Cliente": "first",
            "faturamento_total": "sum",
            "faturamento_90d": "sum",
            "faturamento_180d": "sum",
            "faturamento_90d_anterior": "sum",
            "pedidos": "sum",
            "itens_vendidos": "sum",
            "mix_produtos": "max",
            "ultima_compra": "max",
            "ticket_medio": "mean",
            "produtos_comprados": "first",
            "evolution_status": "first",
            "fidelidade_score": "max",
            "customer_tier": "first",
            "cliente_status": "first"
        }

        agg = {k: v for k, v in agg.items() if k in df.columns}

        result = (
            df.groupby(["Empresa", "codigo_cliente"], as_index=False)
            .agg(agg)
        )

        if "dias_sem_compra" in df.columns:
            result["dias_sem_compra"] = result["ultima_compra"].apply(
                lambda x: (pd.Timestamp(datetime.today().date()) - pd.to_datetime(x)).days
                if pd.notnull(x) else None
            )

        if "faturamento_90d" in result.columns and "faturamento_90d_anterior" in result.columns:
            result["variacao_faturamento_90d"] = result.apply(
                lambda row: (
                    (row["faturamento_90d"] - row["faturamento_90d_anterior"]) /
                    row["faturamento_90d_anterior"]
                    if row["faturamento_90d_anterior"] > 0
                    else 0
                ),
                axis=1
            )

        return result

    def _build_category_daily(self, pedidos):

        columns = [
            "sale_date",
            "Empresa",
            "categoria",
            "faturamento_total",
            "pedidos",
            "itens_vendidos",
            "clientes",
            "produtos"
        ]

        if pedidos is None or pedidos.empty:
            return pd.DataFrame(columns=columns)

        category_column = self._first_existing_column(
            pedidos,
            [
                "Classificacao",
                "classificacao",
                "ClassificaÃ§Ã£o"
            ]
        )

        if category_column is None:
            raise KeyError(
                "NÃ£o foi possÃ­vel gerar mart_sales_category_daily. "
                "Nenhuma coluna de classificaÃ§Ã£o foi encontrada."
            )

        required_columns = [
            "Data",
            "Empresa",
            category_column,
            "Valor_total_Unitario",
            "numero_pedido",
            "codigo_item",
            "codigo_cliente",
            "prod_codigo"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in pedidos.columns
        ]

        if missing_columns:
            raise KeyError(
                "NÃ£o foi possÃ­vel gerar mart_sales_category_daily. "
                "Colunas ausentes: "
                + ", ".join(missing_columns)
            )

        df = pedidos[required_columns].copy()

        df["Data"] = pd.to_datetime(
            df["Data"],
            errors="coerce"
        )

        df["Valor_total_Unitario"] = pd.to_numeric(
            df["Valor_total_Unitario"],
            errors="coerce"
        ).fillna(0)

        df["categoria"] = (
            df[category_column]
            .fillna("SEM CLASSIFICACAO")
            .astype(str)
            .str.strip()
        )

        df.loc[
            df["categoria"].eq(""),
            "categoria"
        ] = "SEM CLASSIFICACAO"

        df = df[
            df["Data"].notna()
            & df["Empresa"].notna()
            & df["categoria"].notna()
        ].copy()

        if df.empty:
            return pd.DataFrame(columns=columns)

        df["sale_date"] = df["Data"].dt.date

        def aggregate(base_df, group_columns, empresa_value=None):

            result = (
                base_df
                .groupby(
                    group_columns,
                    dropna=False,
                    as_index=False
                )
                .agg(
                    faturamento_total=(
                        "Valor_total_Unitario",
                        "sum"
                    ),
                    pedidos=(
                        "numero_pedido",
                        "nunique"
                    ),
                    itens_vendidos=(
                        "codigo_item",
                        "count"
                    ),
                    clientes=(
                        "codigo_cliente",
                        "nunique"
                    ),
                    produtos=(
                        "prod_codigo",
                        "nunique"
                    )
                )
            )

            if empresa_value is not None:
                result["Empresa"] = empresa_value

            return result

        by_company = aggregate(
            df,
            [
                "sale_date",
                "Empresa",
                "categoria"
            ]
        )

        total = aggregate(
            df,
            [
                "sale_date",
                "categoria"
            ],
            empresa_value="TOTAL"
        )

        daily = pd.concat(
            [
                total,
                by_company
            ],
            ignore_index=True,
            sort=False
        )

        daily["Empresa"] = (
            daily["Empresa"]
            .astype(str)
            .str.strip()
        )

        daily["categoria"] = (
            daily["categoria"]
            .astype(str)
            .str.strip()
        )

        daily = daily[
            daily["Empresa"].ne("")
            & daily["categoria"].ne("")
        ].copy()

        daily = (
            daily
            .sort_values(
                [
                    "sale_date",
                    "Empresa",
                    "categoria"
                ],
                ascending=True
            )
            .drop_duplicates(
                subset=[
                    "sale_date",
                    "Empresa",
                    "categoria"
                ],
                keep="first"
            )
            .reset_index(drop=True)
        )

        return daily[columns]

    @staticmethod
    def _category_daily_key(record):
        return (
            str(record.get("reference_date") or ""),
            str(record.get("sale_date") or ""),
            str(record.get("empresa") or ""),
            str(record.get("categoria") or "")
        )

    @staticmethod
    def _category_daily_comparable(record):
        def optional_float(value, decimals):
            if value is None:
                return None
            return round(float(value), decimals)

        def optional_int(value):
            if value is None:
                return None
            return int(value)

        return {
            "reference_date": str(record.get("reference_date") or ""),
            "sale_date": str(record.get("sale_date") or ""),
            "empresa": str(record.get("empresa") or ""),
            "categoria": str(record.get("categoria") or ""),
            "faturamento_total": optional_float(record.get("faturamento_total"), 2),
            "pedidos": optional_int(record.get("pedidos")),
            "itens_vendidos": optional_int(record.get("itens_vendidos")),
            "clientes": optional_int(record.get("clientes")),
            "produtos": optional_int(record.get("produtos")),
        }

    def _sync_category_daily_diff(self, records, reference_date):
        started_at = perf_counter()

        current_rows = self.supabase.select_rows_paginated(
            "mart_sales_category_daily",
            columns=(
                "id,reference_date,sale_date,empresa,categoria,"
                "faturamento_total,pedidos,itens_vendidos,clientes,produtos"
            ),
            filters={"reference_date": reference_date},
            order_by="id",
            page_size=1000,
        )

        generated_by_key = {}
        duplicate_generated_keys = 0
        for record in records:
            key = self._category_daily_key(record)
            if key in generated_by_key:
                duplicate_generated_keys += 1
            generated_by_key[key] = record

        current_by_key = {}
        duplicate_current_keys = 0
        for record in current_rows:
            key = self._category_daily_key(record)
            if key in current_by_key:
                duplicate_current_keys += 1
            current_by_key[key] = record

        if duplicate_generated_keys or duplicate_current_keys:
            raise RuntimeError(
                "Category Daily incremental abortado: foram encontradas chaves duplicadas."
            )

        generated_keys = set(generated_by_key)
        current_keys = set(current_by_key)
        new_keys = generated_keys - current_keys
        removed_keys = current_keys - generated_keys
        common_keys = generated_keys & current_keys

        changed_keys = {
            key for key in common_keys
            if self._category_daily_comparable(generated_by_key[key])
            != self._category_daily_comparable(current_by_key[key])
        }

        unchanged_count = len(common_keys) - len(changed_keys)
        upsert_records = [
            generated_by_key[key]
            for key in (sorted(new_keys) + sorted(changed_keys))
        ]
        removed_ids = [
            current_by_key[key]["id"]
            for key in sorted(removed_keys)
            if current_by_key[key].get("id") is not None
        ]

        if len(removed_ids) != len(removed_keys):
            raise RuntimeError(
                "Category Daily incremental abortado: nem todos os removidos possuem id vÃ¡lido."
            )

        compare_elapsed = perf_counter() - started_at
        write_started_at = perf_counter()

        self.supabase.upsert_batches(
            table_name="mart_sales_category_daily",
            data=upsert_records,
            conflict_columns="reference_date,sale_date,empresa,categoria",
            batch_size=500,
        )

        self.supabase.delete_ids_batches(
            table_name="mart_sales_category_daily",
            ids=removed_ids,
            id_column="id",
            batch_size=250,
        )

        write_elapsed = perf_counter() - write_started_at
        total_elapsed = perf_counter() - started_at

        print()
        print("=" * 60)
        print("CATEGORY DAILY - SYNC DIFERENCIAL")
        print("=" * 60)
        print(f"Snapshot anterior:   {len(current_rows):,}")
        print(f"Gerado agora:        {len(records):,}")
        print(f"Iguais:              {unchanged_count:,}")
        print(f"Novos:               {len(new_keys):,}")
        print(f"Alterados:           {len(changed_keys):,}")
        print(f"Removidos:           {len(removed_keys):,}")
        print(f"Upserts executados:  {len(upsert_records):,}")
        print(f"Deletes executados:  {len(removed_ids):,}")
        print(f"ComparaÃ§Ã£o/leitura:  {compare_elapsed:.2f}s")
        print(f"Escrita diferencial: {write_elapsed:.2f}s")
        print(f"Tempo total sync:    {total_elapsed:.2f}s ({total_elapsed / 60:.2f} min)")
        print("=" * 60)

        return len(records)

    def _save_category_daily(
        self,
        category_daily_df,
        reference_date
    ):

        filters = {
            "reference_date": reference_date
        }

        records = []

        if (
            category_daily_df is not None
            and not category_daily_df.empty
        ):
            for _, row in category_daily_df.iterrows():

                sale_date = pd.to_datetime(
                    row["sale_date"],
                    errors="coerce"
                )

                if pd.isna(sale_date):
                    continue

                records.append({
                    "reference_date": reference_date,
                    "sale_date": sale_date.date().isoformat(),
                    "empresa": row["Empresa"],
                    "categoria": row["categoria"],
                    "faturamento_total": round(
                        float(row["faturamento_total"]),
                        2
                    ),
                    "pedidos": int(row["pedidos"]),
                    "itens_vendidos": int(
                        row["itens_vendidos"]
                    ),
                    "clientes": int(row["clientes"]),
                    "produtos": int(row["produtos"])
                })

        print(
            "  Publicando categorias diÃ¡rias: "
            f"{len(records):,} registros"
        )

        return self._sync_category_daily_diff(
            records=records,
            reference_date=reference_date
        )

    @staticmethod
    def _first_existing_column(dataframe, candidates):

        for column in candidates:
            if column in dataframe.columns:
                return column

        return None

    def _build_product_daily(self, pedidos):

        columns = [
            "sale_date",
            "Empresa",
            "prod_codigo",
            "produto",
            "Classificacao",
            "unidade",
            "faturamento_total",
            "quantidade",
            "pedidos",
            "clientes"
        ]

        if pedidos is None or pedidos.empty:
            return pd.DataFrame(columns=columns)

        quantity_column = self._first_existing_column(
            pedidos,
            [
                "quantidade",
                "Quantidade",
                "qtd",
                "Qtd",
                "quantidade_item"
            ]
        )

        classification_column = self._first_existing_column(
            pedidos,
            [
                "Classificacao",
                "classificacao",
                "ClassificaÃ§Ã£o"
            ]
        )

        unit_column = self._first_existing_column(
            pedidos,
            [
                "unidade",
                "Unidade",
                "UNIDADE"
            ]
        )

        required_columns = [
            "Data",
            "Empresa",
            "prod_codigo",
            "produto",
            "Valor_total_Unitario",
            "numero_pedido",
            "codigo_cliente"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in pedidos.columns
        ]

        if missing_columns:
            raise KeyError(
                "NÃ£o foi possÃ­vel gerar mart_sales_product_daily. "
                "Colunas ausentes: "
                + ", ".join(missing_columns)
            )

        selected_columns = required_columns.copy()

        for optional_column in [
            quantity_column,
            classification_column,
            unit_column
        ]:
            if (
                optional_column is not None
                and optional_column not in selected_columns
            ):
                selected_columns.append(optional_column)

        df = pedidos[selected_columns].copy()

        df["Data"] = pd.to_datetime(
            df["Data"],
            errors="coerce"
        )

        df["Valor_total_Unitario"] = pd.to_numeric(
            df["Valor_total_Unitario"],
            errors="coerce"
        ).fillna(0)

        if quantity_column is not None:
            df["_quantidade"] = pd.to_numeric(
                df[quantity_column],
                errors="coerce"
            ).fillna(0)
        else:
            df["_quantidade"] = 1

        df["_classificacao"] = (
            df[classification_column]
            if classification_column is not None
            else None
        )

        df["_unidade"] = (
            df[unit_column]
            if unit_column is not None
            else None
        )

        df = df[
            df["Data"].notna()
            & df["Empresa"].notna()
            & df["prod_codigo"].notna()
            & df["produto"].notna()
        ].copy()

        if df.empty:
            return pd.DataFrame(columns=columns)

        df["sale_date"] = df["Data"].dt.date

        def aggregate(base_df, group_columns, empresa_value=None):

            result = (
                base_df
                .sort_values(
                    [
                        "sale_date",
                        "Empresa",
                        "prod_codigo",
                        "produto"
                    ],
                    ascending=True
                )
                .groupby(
                    group_columns,
                    dropna=False,
                    as_index=False
                )
                .agg(
                    produto=(
                        "produto",
                        "first"
                    ),
                    Classificacao=(
                        "_classificacao",
                        "first"
                    ),
                    unidade=(
                        "_unidade",
                        "first"
                    ),
                    faturamento_total=(
                        "Valor_total_Unitario",
                        "sum"
                    ),
                    quantidade=(
                        "_quantidade",
                        "sum"
                    ),
                    pedidos=(
                        "numero_pedido",
                        "nunique"
                    ),
                    clientes=(
                        "codigo_cliente",
                        "nunique"
                    )
                )
            )

            if empresa_value is not None:
                result["Empresa"] = empresa_value

            return result

        by_company = aggregate(
            df,
            [
                "sale_date",
                "Empresa",
                "prod_codigo"
            ]
        )

        total = aggregate(
            df,
            [
                "sale_date",
                "prod_codigo"
            ],
            empresa_value="TOTAL"
        )

        daily = pd.concat(
            [
                total,
                by_company
            ],
            ignore_index=True,
            sort=False
        )

        daily["prod_codigo"] = (
            daily["prod_codigo"]
            .astype(str)
            .str.strip()
        )

        daily["produto"] = (
            daily["produto"]
            .astype(str)
            .str.strip()
        )

        daily["Empresa"] = (
            daily["Empresa"]
            .astype(str)
            .str.strip()
        )

        daily = daily[
            daily["prod_codigo"].ne("")
            & daily["produto"].ne("")
            & daily["Empresa"].ne("")
        ].copy()

        daily = (
            daily
            .sort_values(
                [
                    "sale_date",
                    "Empresa",
                    "prod_codigo"
                ],
                ascending=True
            )
            .drop_duplicates(
                subset=[
                    "sale_date",
                    "Empresa",
                    "prod_codigo"
                ],
                keep="first"
            )
            .reset_index(drop=True)
        )

        return daily[columns]

    @staticmethod
    def _product_daily_key(record):
        return (
            str(record.get("reference_date") or ""),
            str(record.get("sale_date") or ""),
            str(record.get("empresa") or ""),
            str(record.get("prod_codigo") or "")
        )

    @staticmethod
    def _product_daily_comparable(record):
        def optional_float(value, decimals):
            if value is None:
                return None
            return round(float(value), decimals)

        def optional_int(value):
            if value is None:
                return None
            return int(value)

        def optional_text(value):
            if value is None:
                return None
            return str(value)

        return {
            "reference_date": str(record.get("reference_date") or ""),
            "sale_date": str(record.get("sale_date") or ""),
            "empresa": str(record.get("empresa") or ""),
            "prod_codigo": str(record.get("prod_codigo") or ""),
            "produto": optional_text(record.get("produto")),
            "classificacao": optional_text(record.get("classificacao")),
            "unidade": optional_text(record.get("unidade")),
            "faturamento_total": optional_float(record.get("faturamento_total"), 2),
            "quantidade": optional_float(record.get("quantidade"), 4),
            "pedidos": optional_int(record.get("pedidos")),
            "clientes": optional_int(record.get("clientes")),
        }

    def _sync_product_daily_diff(self, records, reference_date):
        started_at = perf_counter()

        current_rows = self.supabase.select_rows_paginated(
            "mart_sales_product_daily",
            columns=(
                "id,reference_date,sale_date,empresa,prod_codigo,"
                "produto,classificacao,unidade,faturamento_total,"
                "quantidade,pedidos,clientes"
            ),
            filters={"reference_date": reference_date},
            order_by="id",
            page_size=1000,
        )

        generated_by_key = {}
        duplicate_generated_keys = 0
        for record in records:
            key = self._product_daily_key(record)
            if key in generated_by_key:
                duplicate_generated_keys += 1
            generated_by_key[key] = record

        current_by_key = {}
        duplicate_current_keys = 0
        for record in current_rows:
            key = self._product_daily_key(record)
            if key in current_by_key:
                duplicate_current_keys += 1
            current_by_key[key] = record

        if duplicate_generated_keys or duplicate_current_keys:
            raise RuntimeError(
                "Product Daily incremental abortado: foram encontradas chaves duplicadas."
            )

        generated_keys = set(generated_by_key)
        current_keys = set(current_by_key)

        new_keys = generated_keys - current_keys
        removed_keys = current_keys - generated_keys
        common_keys = generated_keys & current_keys

        changed_keys = {
            key
            for key in common_keys
            if self._product_daily_comparable(generated_by_key[key])
            != self._product_daily_comparable(current_by_key[key])
        }

        unchanged_count = len(common_keys) - len(changed_keys)

        upsert_records = [
            generated_by_key[key]
            for key in (sorted(new_keys) + sorted(changed_keys))
        ]

        removed_ids = [
            current_by_key[key]["id"]
            for key in sorted(removed_keys)
            if current_by_key[key].get("id") is not None
        ]

        if len(removed_ids) != len(removed_keys):
            raise RuntimeError(
                "Product Daily incremental abortado: nem todos os removidos possuem id vÃ¡lido."
            )

        compare_elapsed = perf_counter() - started_at
        write_started_at = perf_counter()

        self.supabase.upsert_batches(
            table_name="mart_sales_product_daily",
            data=upsert_records,
            conflict_columns="reference_date,sale_date,empresa,prod_codigo",
            batch_size=500,
        )

        self.supabase.delete_ids_batches(
            table_name="mart_sales_product_daily",
            ids=removed_ids,
            id_column="id",
            batch_size=250,
        )

        write_elapsed = perf_counter() - write_started_at
        total_elapsed = perf_counter() - started_at

        print()
        print("=" * 60)
        print("PRODUCT DAILY - SYNC DIFERENCIAL")
        print("=" * 60)
        print(f"Snapshot anterior:   {len(current_rows):,}")
        print(f"Gerado agora:        {len(records):,}")
        print(f"Iguais:              {unchanged_count:,}")
        print(f"Novos:               {len(new_keys):,}")
        print(f"Alterados:           {len(changed_keys):,}")
        print(f"Removidos:           {len(removed_keys):,}")
        print(f"Upserts executados:  {len(upsert_records):,}")
        print(f"Deletes executados:  {len(removed_ids):,}")
        print(f"ComparaÃ§Ã£o/leitura:  {compare_elapsed:.2f}s")
        print(f"Escrita diferencial: {write_elapsed:.2f}s")
        print(f"Tempo total sync:    {total_elapsed:.2f}s ({total_elapsed / 60:.2f} min)")
        print("=" * 60)

        return len(records)

    def _save_product_daily(
        self,
        product_daily_df,
        reference_date
    ):

        filters = {
            "reference_date": reference_date
        }

        records = []

        if (
            product_daily_df is not None
            and not product_daily_df.empty
        ):
            for _, row in product_daily_df.iterrows():

                sale_date = pd.to_datetime(
                    row["sale_date"],
                    errors="coerce"
                )

                if pd.isna(sale_date):
                    continue

                classificacao = row.get("Classificacao")
                if pd.isna(classificacao):
                    classificacao = None

                unidade = row.get("unidade")
                if pd.isna(unidade):
                    unidade = None

                records.append({
                    "reference_date": reference_date,
                    "sale_date": sale_date.date().isoformat(),
                    "empresa": row["Empresa"],
                    "prod_codigo": str(row["prod_codigo"]),
                    "produto": row["produto"],
                    "classificacao": classificacao,
                    "unidade": unidade,
                    "faturamento_total": round(
                        float(row["faturamento_total"]),
                        2
                    ),
                    "quantidade": round(
                        float(row["quantidade"]),
                        4
                    ),
                    "pedidos": int(row["pedidos"]),
                    "clientes": int(row["clientes"])
                })

        print(
            "  Publicando produtos diÃ¡rios: "
            f"{len(records):,} registros"
        )

        return self._sync_product_daily_diff(
            records=records,
            reference_date=reference_date
        )

    def _build_customer_daily(self, pedidos):

        columns = [
            "sale_date",
            "Empresa",
            "codigo_cliente",
            "Cliente",
            "faturamento_total",
            "pedidos",
            "itens_vendidos",
            "mix_produtos",
            "ultima_compra"
        ]

        if pedidos is None or pedidos.empty:
            return pd.DataFrame(columns=columns)

        required_columns = [
            "Data",
            "Empresa",
            "codigo_cliente",
            "Cliente",
            "Valor_total_Unitario",
            "numero_pedido",
            "codigo_item",
            "prod_codigo"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in pedidos.columns
        ]

        if missing_columns:
            raise KeyError(
                "NÃ£o foi possÃ­vel gerar mart_sales_customer_daily. "
                "Colunas ausentes: "
                + ", ".join(missing_columns)
            )

        df = pedidos[required_columns].copy()

        df["Data"] = pd.to_datetime(
            df["Data"],
            errors="coerce"
        )

        df["Valor_total_Unitario"] = pd.to_numeric(
            df["Valor_total_Unitario"],
            errors="coerce"
        ).fillna(0)

        df = df[
            df["Data"].notna()
            & df["Empresa"].notna()
            & df["codigo_cliente"].notna()
            & df["Cliente"].notna()
        ].copy()

        if df.empty:
            return pd.DataFrame(columns=columns)

        df["sale_date"] = df["Data"].dt.date

        def aggregate(base_df, group_columns, empresa_value=None):

            result = (
                base_df
                .sort_values(
                    [
                        "sale_date",
                        "Empresa",
                        "codigo_cliente",
                        "Cliente"
                    ],
                    ascending=True
                )
                .groupby(
                    group_columns,
                    dropna=False,
                    as_index=False
                )
                .agg(
                    Cliente=(
                        "Cliente",
                        "first"
                    ),
                    faturamento_total=(
                        "Valor_total_Unitario",
                        "sum"
                    ),
                    pedidos=(
                        "numero_pedido",
                        "nunique"
                    ),
                    itens_vendidos=(
                        "codigo_item",
                        "count"
                    ),
                    mix_produtos=(
                        "prod_codigo",
                        "nunique"
                    )
                )
            )

            if empresa_value is not None:
                result["Empresa"] = empresa_value

            result["ultima_compra"] = result["sale_date"]

            return result

        by_company = aggregate(
            df,
            [
                "sale_date",
                "Empresa",
                "codigo_cliente"
            ]
        )

        total = aggregate(
            df,
            [
                "sale_date",
                "codigo_cliente"
            ],
            empresa_value="TOTAL"
        )

        daily = pd.concat(
            [
                total,
                by_company
            ],
            ignore_index=True,
            sort=False
        )

        daily["codigo_cliente"] = (
            daily["codigo_cliente"]
            .astype(str)
            .str.strip()
        )

        daily["Cliente"] = (
            daily["Cliente"]
            .astype(str)
            .str.strip()
        )

        daily["Empresa"] = (
            daily["Empresa"]
            .astype(str)
            .str.strip()
        )

        daily = daily[
            daily["codigo_cliente"].ne("")
            & daily["Cliente"].ne("")
            & daily["Empresa"].ne("")
        ].copy()

        daily = (
            daily
            .sort_values(
                [
                    "sale_date",
                    "Empresa",
                    "codigo_cliente"
                ],
                ascending=True
            )
            .drop_duplicates(
                subset=[
                    "sale_date",
                    "Empresa",
                    "codigo_cliente"
                ],
                keep="first"
            )
            .reset_index(drop=True)
        )

        return daily[columns]

    @staticmethod
    def _customer_daily_key(record):
        return (
            str(record.get("reference_date") or ""),
            str(record.get("sale_date") or ""),
            str(record.get("empresa") or ""),
            str(record.get("codigo_cliente") or "")
        )

    @staticmethod
    def _customer_daily_comparable(record):
        faturamento_total = record.get("faturamento_total")

        if faturamento_total is not None:
            faturamento_total = round(
                float(faturamento_total),
                2
            )

        def optional_int(value):
            if value is None:
                return None
            return int(value)

        return {
            "reference_date": (
                str(record.get("reference_date") or "")
            ),
            "sale_date": (
                str(record.get("sale_date") or "")
            ),
            "empresa": (
                str(record.get("empresa") or "")
            ),
            "codigo_cliente": (
                str(record.get("codigo_cliente") or "")
            ),
            "cliente": (
                None
                if record.get("cliente") is None
                else str(record.get("cliente"))
            ),
            "faturamento_total": faturamento_total,
            "pedidos": optional_int(
                record.get("pedidos")
            ),
            "itens_vendidos": optional_int(
                record.get("itens_vendidos")
            ),
            "mix_produtos": optional_int(
                record.get("mix_produtos")
            ),
            "ultima_compra": (
                None
                if record.get("ultima_compra") is None
                else str(record.get("ultima_compra"))
            )
        }

    def _sync_customer_daily_diff(
        self,
        records,
        reference_date
    ):

        started_at = perf_counter()

        current_rows = (
            self.supabase.select_rows_paginated(
                "mart_sales_customer_daily",
                columns=(
                    "id,"
                    "reference_date,"
                    "sale_date,"
                    "empresa,"
                    "codigo_cliente,"
                    "cliente,"
                    "faturamento_total,"
                    "pedidos,"
                    "itens_vendidos,"
                    "mix_produtos,"
                    "ultima_compra"
                ),
                filters={
                    "reference_date": reference_date
                },
                order_by="id",
                page_size=1000
            )
        )

        generated_by_key = {}
        duplicate_generated_keys = 0

        for record in records:
            key = self._customer_daily_key(
                record
            )

            if key in generated_by_key:
                duplicate_generated_keys += 1

            generated_by_key[key] = record

        current_by_key = {}
        duplicate_current_keys = 0

        for record in current_rows:
            key = self._customer_daily_key(
                record
            )

            if key in current_by_key:
                duplicate_current_keys += 1

            current_by_key[key] = record

        if (
            duplicate_generated_keys > 0
            or duplicate_current_keys > 0
        ):
            raise RuntimeError(
                "Customer Daily incremental abortado: "
                "foram encontradas chaves duplicadas."
            )

        generated_keys = set(
            generated_by_key
        )
        current_keys = set(
            current_by_key
        )

        new_keys = (
            generated_keys
            - current_keys
        )
        removed_keys = (
            current_keys
            - generated_keys
        )
        common_keys = (
            generated_keys
            & current_keys
        )

        changed_keys = {
            key
            for key in common_keys
            if (
                self._customer_daily_comparable(
                    generated_by_key[key]
                )
                !=
                self._customer_daily_comparable(
                    current_by_key[key]
                )
            )
        }

        unchanged_count = (
            len(common_keys)
            - len(changed_keys)
        )

        upsert_records = [
            generated_by_key[key]
            for key in (
                sorted(new_keys)
                + sorted(changed_keys)
            )
        ]

        removed_ids = [
            current_by_key[key]["id"]
            for key in sorted(removed_keys)
            if current_by_key[key].get("id") is not None
        ]

        if len(removed_ids) != len(removed_keys):
            raise RuntimeError(
                "Customer Daily incremental abortado: "
                "nem todos os removidos possuem id vÃ¡lido."
            )

        compare_elapsed = (
            perf_counter()
            - started_at
        )

        write_started_at = perf_counter()

        self.supabase.upsert_batches(
            table_name="mart_sales_customer_daily",
            data=upsert_records,
            conflict_columns=(
                "reference_date,"
                "sale_date,"
                "empresa,"
                "codigo_cliente"
            ),
            batch_size=500
        )

        self.supabase.delete_ids_batches(
            table_name="mart_sales_customer_daily",
            ids=removed_ids,
            id_column="id",
            batch_size=250
        )

        write_elapsed = (
            perf_counter()
            - write_started_at
        )

        total_elapsed = (
            perf_counter()
            - started_at
        )

        print()
        print("=" * 60)
        print(
            "CUSTOMER DAILY - SYNC DIFERENCIAL"
        )
        print("=" * 60)
        print(
            f"Snapshot anterior:   "
            f"{len(current_rows):,}"
        )
        print(
            f"Gerado agora:        "
            f"{len(records):,}"
        )
        print(
            f"Iguais:              "
            f"{unchanged_count:,}"
        )
        print(
            f"Novos:               "
            f"{len(new_keys):,}"
        )
        print(
            f"Alterados:           "
            f"{len(changed_keys):,}"
        )
        print(
            f"Removidos:           "
            f"{len(removed_keys):,}"
        )
        print(
            f"Upserts executados:  "
            f"{len(upsert_records):,}"
        )
        print(
            f"Deletes executados:  "
            f"{len(removed_ids):,}"
        )
        print(
            f"ComparaÃ§Ã£o/leitura:  "
            f"{compare_elapsed:.2f}s"
        )
        print(
            f"Escrita diferencial: "
            f"{write_elapsed:.2f}s"
        )
        print(
            f"Tempo total sync:    "
            f"{total_elapsed:.2f}s "
            f"({total_elapsed / 60:.2f} min)"
        )
        print("=" * 60)

        return len(records)

    def _save_customer_daily(
        self,
        customer_daily_df,
        reference_date
    ):

        filters = {
            "reference_date": reference_date
        }

        records = []

        if (
            customer_daily_df is not None
            and not customer_daily_df.empty
        ):
            for _, row in customer_daily_df.iterrows():

                sale_date = pd.to_datetime(
                    row["sale_date"],
                    errors="coerce"
                )

                if pd.isna(sale_date):
                    continue

                ultima_compra = pd.to_datetime(
                    row["ultima_compra"],
                    errors="coerce"
                )

                records.append({
                    "reference_date": reference_date,
                    "sale_date": sale_date.date().isoformat(),
                    "empresa": row["Empresa"],
                    "codigo_cliente": str(
                        row["codigo_cliente"]
                    ),
                    "cliente": row["Cliente"],
                    "faturamento_total": round(
                        float(row["faturamento_total"]),
                        2
                    ),
                    "pedidos": int(row["pedidos"]),
                    "itens_vendidos": int(
                        row["itens_vendidos"]
                    ),
                    "mix_produtos": int(
                        row["mix_produtos"]
                    ),
                    "ultima_compra": (
                        None
                        if pd.isna(ultima_compra)
                        else ultima_compra.date().isoformat()
                    )
                })

        print(
            "  Publicando clientes diÃ¡rios: "
            f"{len(records):,} registros"
        )

        return self._sync_customer_daily_diff(
            records=records,
            reference_date=reference_date
        )

    def _normalize_categories(self, category_df):

        if category_df is None or category_df.empty:
            return category_df

        df = category_df.copy()

        return (
            df.groupby(["Empresa", "Categoria"], as_index=False)
            .agg({
                "faturamento_total": "sum",
                "pedidos": "sum",
                "itens_vendidos": "sum",
                "clientes": "sum",
                "produtos": "sum",
                "ticket_medio": "mean"
            })
        )

    def _save_sellers(self, seller_df, filters):

        seller_records = []

        for _, row in seller_df.iterrows():
            seller_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "vendedor": row["Vendedor"],
                "empresa": "TOTAL",
                "empresa_breakdown": row["empresa_breakdown"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("sales_seller_ranking_snapshot", filters, seller_records)

    def _save_commercial_sellers(
        self,
        seller_df,
        filters
    ):

        def optional_float(value, decimals=2):

            if value is None or pd.isna(value):
                return None

            return round(
                float(value),
                decimals
            )

        def optional_int(value):

            if value is None or pd.isna(value):
                return None

            return int(value)

        def optional_text(value):

            if value is None or pd.isna(value):
                return None

            text = str(value).strip()

            return text if text else None

        records = []

        if seller_df is not None and not seller_df.empty:

            for _, row in seller_df.iterrows():

                records.append({
                    "reference_date": (
                        filters["reference_date"]
                    ),
                    "period_type": (
                        filters["period_type"]
                    ),

                    "seller_key": row["seller_key"],
                    "vendedor": row["Vendedor"],

                    "faturamento_total": round(
                        float(row["faturamento_total"]),
                        2
                    ),
                    "pedidos": int(row["pedidos"]),
                    "itens_vendidos": int(
                        row["itens_vendidos"]
                    ),
                    "clientes": int(row["clientes"]),
                    "mix_produtos": int(
                        row["mix_produtos"]
                    ),
                    "ticket_medio": round(
                        float(row["ticket_medio"]),
                        2
                    ),

                    "empresa_breakdown": (
                        row["empresa_breakdown"]
                    ),

                    "meta_mensal": round(
                        float(row["meta_mensal"]),
                        2
                    ),
                    "supermeta": round(
                        float(row["supermeta"]),
                        2
                    ),
                    "hipermeta": round(
                        float(row["hipermeta"]),
                        2
                    ),

                    "atingimento": round(
                        float(row["atingimento"]),
                        6
                    ),
                    "atingimento_supermeta": round(
                        float(
                            row["atingimento_supermeta"]
                        ),
                        6
                    ),
                    "atingimento_hipermeta": round(
                        float(
                            row["atingimento_hipermeta"]
                        ),
                        6
                    ),

                    "gap_meta": round(
                        float(row["gap_meta"]),
                        2
                    ),
                    "gap_supermeta": round(
                        float(row["gap_supermeta"]),
                        2
                    ),
                    "gap_hipermeta": round(
                        float(row["gap_hipermeta"]),
                        2
                    ),

                    "meta_valida": bool(
                        row["meta_valida"]
                    ),
                    "meta_batida": bool(
                        row["meta_batida"]
                    ),
                    "arena_eligible": bool(
                        row["arena_eligible"]
                    ),

                    "status_meta": row["status_meta"],

                    "ranking_faturamento": (
                        optional_int(
                            row.get(
                                "ranking_faturamento"
                            )
                        )
                    ),
                    "ranking_atingimento": (
                        optional_int(
                            row.get(
                                "ranking_atingimento"
                            )
                        )
                    ),

                    "pace_applicable": bool(
                        row.get(
                            "pace_applicable",
                            False
                        )
                    ),
                    "dias_uteis_mes": (
                        optional_int(
                            row.get(
                                "dias_uteis_mes"
                            )
                        )
                    ),
                    "dias_uteis_decorridos": (
                        optional_int(
                            row.get(
                                "dias_uteis_decorridos"
                            )
                        )
                    ),
                    "dias_uteis_restantes": (
                        optional_int(
                            row.get(
                                "dias_uteis_restantes"
                            )
                        )
                    ),

                    "meta_diaria": (
                        optional_float(
                            row.get("meta_diaria")
                        )
                    ),
                    "ritmo_atual": (
                        optional_float(
                            row.get("ritmo_atual")
                        )
                    ),
                    "ritmo_necessario": (
                        optional_float(
                            row.get(
                                "ritmo_necessario"
                            )
                        )
                    ),
                    "projecao_fechamento": (
                        optional_float(
                            row.get(
                                "projecao_fechamento"
                            )
                        )
                    ),
                    "projecao_atingimento": (
                        optional_float(
                            row.get(
                                "projecao_atingimento"
                            ),
                            decimals=6
                        )
                    ),
                    "projecao_atinge_meta": bool(
                        row.get(
                            "projecao_atinge_meta",
                            False
                        )
                    ),
                                        "status_projecao": row.get(
                        "status_projecao",
                        "nao_aplicavel"
                    ),
                    "arena_position": (
                        optional_int(
                            row.get(
                                "arena_position"
                            )
                        )
                    ),
                    "arena_score": (
                        optional_float(
                            row.get(
                                "arena_score"
                            ),
                            decimals=6
                        )
                    ),
                    "arena_medal": (
                        optional_text(
                            row.get("arena_medal")
                        )
                    ),
                    "arena_level": (
                        optional_text(
                            row.get("arena_level")
                        )
                    ),
                    "arena_gap_first_pp": (
                        optional_float(
                            row.get(
                                "arena_gap_first_pp"
                            )
                        )
                    ),
                    "arena_gap_next_pp": (
                        optional_float(
                            row.get(
                                "arena_gap_next_pp"
                            )
                        )
                    ),
                    "arena_is_leader": (
                        False
                        if pd.isna(
                            row.get("arena_is_leader")
                        )
                        else bool(
                            row.get("arena_is_leader")
                        )
                    ),
                    "arena_highlight": (
                        optional_text(
                            row.get("arena_highlight")
                        )
                    ),
                        "seller_scorecards": (
                        None
                        if pd.isna(
                            row.get("seller_scorecards")
                        )
                        else json.loads(
                            row.get("seller_scorecards")
                        )
                    ),
                    "seller_health_score": (
                        optional_float(
                            row.get(
                                "seller_health_score"
                            )
                        )
                        or 0
                    ),
                    "seller_health_status": (
                        optional_text(
                            row.get(
                                "seller_health_status"
                            )
                        )
                        or "critical"
                    ),
                    "seller_health_label": (
                        optional_text(
                            row.get(
                                "seller_health_label"
                            )
                        )
                        or "CrÃ­tico"
                    ),
                                        "seller_insights": (
                        None
                        if pd.isna(
                            row.get("seller_insights")
                        )
                        else json.loads(
                            row.get("seller_insights")
                        )
                    ),
                    "seller_primary_insight": (
                        optional_text(
                            row.get(
                                "seller_primary_insight"
                            )
                        )
                    ),
                    "seller_primary_support": (
                        optional_text(
                            row.get(
                                "seller_primary_support"
                            )
                        )
                    ),
                    "seller_primary_severity": (
                        optional_text(
                            row.get(
                                "seller_primary_severity"
                            )
                        )
                        or "neutral"
                    ),
                    "seller_recommended_action": (
                        optional_text(
                            row.get(
                                "seller_recommended_action"
                            )
                        )
                    ),
                    "seller_insight_count": (
                        optional_int(
                            row.get(
                                "seller_insight_count"
                            )
                        )
                        or 0
                    )
,
                    "seller_team_benchmark": (
                        None
                        if pd.isna(
                            row.get(
                                "seller_team_benchmark"
                            )
                        )
                        else json.loads(
                            row.get(
                                "seller_team_benchmark"
                            )
                        )
                    ),
                    "seller_vs_team": (
                        None
                        if pd.isna(
                            row.get(
                                "seller_vs_team"
                            )
                        )
                        else json.loads(
                            row.get(
                                "seller_vs_team"
                            )
                        )
                    ),
                    "seller_next_opponent": (
                        None
                        if pd.isna(
                            row.get(
                                "seller_next_opponent"
                            )
                        )
                        else json.loads(
                            row.get(
                                "seller_next_opponent"
                            )
                        )
                    )
                })

        print(
            "  Publicando Seller Intelligence: "
            f"{len(records):,} registros "
            f"({filters['period_type']})"
        )

        self.supabase.replace_snapshot(
            "mart_commercial_seller_snapshot",
            filters,
            records
        )

        return len(records)

    def _save_companies(self, company_df, filters):

        company_records = []

        for _, row in company_df.iterrows():
            company_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("mart_sales_company_snapshot", filters, company_records)

    def _save_products(self, product_df, filters):

        product_records = []

        for _, row in product_df.iterrows():
            product_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "prod_codigo": row["prod_codigo"],
                "produto": row["produto"],
                "classificacao": row["Classificacao"],
                "unidade": row["unidade"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "quantidade": float(row["quantidade"]),
                "pedidos": int(row["pedidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("mart_sales_product_snapshot", filters, product_records)

    def _save_customers(self, customer_df, filters):

        customer_records = []

        for _, row in customer_df.iterrows():

            ultima_compra = None
            if pd.notnull(row["ultima_compra"]):
                try:
                    ultima_compra = pd.to_datetime(row["ultima_compra"]).date().isoformat()
                except Exception:
                    ultima_compra = None

            dias_sem_compra = row.get("dias_sem_compra")
            if pd.isna(dias_sem_compra):
                dias_sem_compra = None

            customer_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "codigo_cliente": str(row["codigo_cliente"]),
                "cliente": row["Cliente"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "faturamento_90d": round(float(row.get("faturamento_90d", 0)), 2),
                "faturamento_180d": round(float(row.get("faturamento_180d", 0)), 2),
                "faturamento_90d_anterior": round(float(row.get("faturamento_90d_anterior", 0)), 2),
                "variacao_faturamento_90d": round(float(row.get("variacao_faturamento_90d", 0)), 4),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "mix_produtos": int(row["mix_produtos"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2),
                "ultima_compra": ultima_compra,
                "dias_sem_compra": None if dias_sem_compra is None else int(dias_sem_compra),
                "produtos_comprados": row.get("produtos_comprados"),
                "evolution_status": row.get("evolution_status"),
                "fidelidade_score": round(float(row.get("fidelidade_score", 0)), 2),
                "customer_tier": row.get("customer_tier"),
                "cliente_status": row.get("cliente_status")
            })

        self.supabase.replace_snapshot("mart_sales_customer_snapshot", filters, customer_records)

    def _save_categories(self, category_df, filters):

        category_records = []

        for _, row in category_df.iterrows():
            category_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "categoria": row["Categoria"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "produtos": int(row["produtos"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("mart_sales_category_snapshot", filters, category_records)