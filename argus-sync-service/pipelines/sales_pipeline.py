from datetime import datetime
from time import perf_counter
import pandas as pd

from config.periods import MVP_PERIODS, resolve_window

from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer
from extractors.meta_extractor import MetaExtractor
from pipelines.sales_mart_pipeline import SalesMartPipeline
from pipelines.commercial_intelligence_pipeline import CommercialIntelligencePipeline
from pipelines.sales_history_pipeline import SalesHistoryPipeline
from pipelines.revenue_intelligence_pipeline import (
    RevenueIntelligencePipeline,
)

def _timed_stage(label, callback):
    started_at = perf_counter()
    result = callback()
    elapsed = perf_counter() - started_at

    print(
        f"[SALES TIMING] {label}: "
        f"{elapsed:.2f}s "
        f"({elapsed / 60:.2f} min)"
    )

    return result, elapsed


class SalesPipeline:

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(self):

        sales_started_at = perf_counter()
        stage_timings = {}
        period_timings = {}

        hoje = datetime.today().date()

        pedidos, stage_timings["pedido_extract"] = _timed_stage(
            "PedidoExtractor.extract",
            lambda: PedidoExtractor(
                self.sql_connector
            ).extract(),
        )

        pedidos, stage_timings["pedido_filter"] = _timed_stage(
            "PedidoTransformer.filter_revenue_orders",
            lambda: PedidoTransformer().filter_revenue_orders(
                pedidos
            ),
        )

        normalize_started_at = perf_counter()

        pedidos["Data"] = pd.to_datetime(
            pedidos["Data"],
            errors="coerce"
        )
        pedidos = pedidos[
            pedidos["Data"].notna()
        ].copy()

        stage_timings["pedido_date_normalization"] = (
            perf_counter() - normalize_started_at
        )

        print(
            "[SALES TIMING] Normalização de Data: "
            f"{stage_timings['pedido_date_normalization']:.2f}s "
            f"({stage_timings['pedido_date_normalization'] / 60:.2f} min)"
        )

        meta_df, stage_timings["meta_extract"] = _timed_stage(
            "MetaExtractor.extract",
            lambda: MetaExtractor(
                self.sql_connector
            ).extract(),
        )

        sales_marts = SalesMartPipeline(
            self.supabase
        )
        intelligence = CommercialIntelligencePipeline(
            self.supabase
        )

        history_result, stage_timings["sales_history"] = _timed_stage(
            "SalesHistoryPipeline.run",
            lambda: SalesHistoryPipeline(
                self.supabase
            ).run(pedidos),
        )

        revenue_result, stage_timings["revenue_intelligence"] = _timed_stage(
            "RevenueIntelligencePipeline.run",
            lambda: RevenueIntelligencePipeline(
                sql_connector=self.sql_connector,
                supabase_connector=self.supabase,
            ).run(
                pedidos=pedidos
            ),
        )

        current_month_result = None
        current_month_intelligence = None
        period_results = {}

        periods_to_generate = (
            ["historico"]
            + list(MVP_PERIODS)
        )

        for period_type in periods_to_generate:

            period_started_at = perf_counter()

            slice_started_at = perf_counter()

            if period_type == "historico":
                pedidos_periodo = pedidos.copy()
                date_from = (
                    pedidos_periodo["Data"]
                    .min()
                    .date()
                )
                date_to = (
                    pedidos_periodo["Data"]
                    .max()
                    .date()
                )
            else:
                window = resolve_window(
                    period_type,
                    hoje
                )
                pedidos_periodo = pedidos[
                    (
                        pedidos["Data"].dt.date
                        >= window.date_from
                    )
                    &
                    (
                        pedidos["Data"].dt.date
                        <= window.date_to
                    )
                ].copy()
                date_from = window.date_from
                date_to = window.date_to

            slice_elapsed = (
                perf_counter()
                - slice_started_at
            )

            print(
                f"  Gerando marts de vendas: {period_type} "
                f"({date_from} até {date_to}) "
                f"- {len(pedidos_periodo)} registros"
            )

            mart_result, mart_elapsed = _timed_stage(
                f"{period_type} | SalesMartPipeline.run",
                lambda: sales_marts.run(
                    pedidos_periodo,
                    meta_df=meta_df,
                    period_type=period_type
                ),
            )

            intelligence_result, intelligence_elapsed = _timed_stage(
                f"{period_type} | CommercialIntelligencePipeline.run",
                lambda: intelligence.run(
                    mart_result["seller_df"],
                    mart_result["company_df"],
                    mart_result["product_df_all"],
                    mart_result["customer_df_all"],
                    mart_result["category_df_all"],
                    period_type=period_type
                ),
            )

            period_elapsed = (
                perf_counter()
                - period_started_at
            )

            period_timings[period_type] = {
                "slice": slice_elapsed,
                "mart": mart_elapsed,
                "intelligence": intelligence_elapsed,
                "total": period_elapsed,
            }

            print(
                f"[SALES TIMING] {period_type} | "
                f"recorte={slice_elapsed:.2f}s | "
                f"mart={mart_elapsed:.2f}s | "
                f"intelligence={intelligence_elapsed:.2f}s | "
                f"total={period_elapsed:.2f}s"
            )

            period_results[period_type] = {
                "commercial_sellers": (
                    mart_result[
                        "commercial_seller_records"
                    ]
                ),
                "seller_ranking": len(
                    mart_result["seller_df"]
                ),
                "companies": len(
                    mart_result["company_df"]
                ),
                "products": len(
                    mart_result["product_df"]
                ),
                "customers": len(
                    mart_result["customer_df"]
                ),
                "categories": len(
                    mart_result["category_df"]
                ),
                **intelligence_result
            }

            if period_type == "current_month":
                current_month_result = mart_result
                current_month_intelligence = (
                    intelligence_result
                )

        if (
            current_month_result is None
            or current_month_intelligence is None
        ):
            raise RuntimeError(
                "current_month não foi gerado."
            )

        sales_elapsed = (
            perf_counter()
            - sales_started_at
        )

        print()
        print("=" * 60)
        print("SALES PIPELINE - TEMPOS INTERNOS")
        print("=" * 60)

        ordered_stages = [
            (
                "Pedido extract",
                "pedido_extract",
            ),
            (
                "Pedido filter",
                "pedido_filter",
            ),
            (
                "Data normalization",
                "pedido_date_normalization",
            ),
            (
                "Meta extract",
                "meta_extract",
            ),
            (
                "Sales History",
                "sales_history",
            ),
            (
                "Revenue Intelligence",
                "revenue_intelligence",
            ),
        ]

        for label, key in ordered_stages:
            elapsed = stage_timings[key]
            print(
                f"{label:<24} "
                f"{elapsed:8.2f}s "
                f"({elapsed / 60:.2f} min)"
            )

        print("-" * 60)

        for period_type in periods_to_generate:
            timing = period_timings[
                period_type
            ]
            print(
                f"{period_type:<18} "
                f"{timing['total']:8.2f}s | "
                f"mart {timing['mart']:8.2f}s | "
                f"intel {timing['intelligence']:8.2f}s"
            )

        print("-" * 60)
        print(
            f"SALES TOTAL              "
            f"{sales_elapsed:8.2f}s "
            f"({sales_elapsed / 60:.2f} min)"
        )

        return {
            "seller_ranking": len(current_month_result["seller_df"]),
                        "commercial_sellers": (
                current_month_result[
                    "commercial_seller_records"
                ]
            ),
            "companies": len(current_month_result["company_df"]),
            "products": len(current_month_result["product_df"]),
            "customers": len(current_month_result["customer_df"]),
            "categories": len(current_month_result["category_df"]),
            "periods_generated": len(period_results),
            **history_result,
            **revenue_result,
            **current_month_intelligence
        }