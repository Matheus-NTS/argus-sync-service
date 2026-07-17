from datetime import datetime

import pandas as pd

from config.periods import (
    MVP_PERIODS,
    resolve_window,
)

from extractors.pedido_extractor import (
    PedidoExtractor,
)
from extractors.produto_extractor import (
    ProdutoExtractor,
)

from transformers.pedido_transformer import (
    PedidoTransformer,
)
from transformers.produto_transformer import (
    ProdutoTransformer,
)

from features.intelligence.profitability.profitability_dataset import (
    ProfitabilityDataset,
)
from features.intelligence.profitability.profitability_overview import (
    ProfitabilityOverview,
)
from features.intelligence.profitability.profitability_dimensions import (
    ProfitabilityDimensions,
)
from features.intelligence.profitability.profitability_risk import (
    ProfitabilityRisk,
)
from features.intelligence.profitability.profitability_recommendations import (
    ProfitabilityRecommendations,
)
from features.intelligence.profitability.profitability_quality import (
    ProfitabilityQuality,
)


class ProfitabilityPipeline:

    METHODOLOGY_NOTE = (
        "Rentabilidade estimada com base no "
        "preco_custo cadastrado atual."
    )

    DETAIL_COLUMNS = [
        "data_venda", "ano", "mes", "ano_mes", "numero_pedido",
        "empresa_key", "empresa_oficial", "vendedor",
        "codigo_cliente_normalizado", "cliente", "codigo_produto",
        "codigo_fabricante", "produto", "produto_fora_escopo",
        "categoria", "curva_abcde", "quantidade",
        "preco_venda_unitario", "preco_venda_medio", "preco_custo",
        "faturamento", "custo_total", "lucro_bruto",
        "margem_percentual", "markup_percentual", "status_custo",
        "custo_valido", "dado_suspeito", "status_analise",
        "elegivel_kpi", "faturamento_analisavel",
        "custo_analisavel", "lucro_analisavel",
        "status_rentabilidade",
    ]

    def __init__(
        self,
        sql_connector,
        supabase_connector
    ):

        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    @staticmethod
    def _safe_float(value, default=0.0):

        if value is None or pd.isna(value):
            return default

        return float(value)

    @staticmethod
    def _serialize_value(value):

        if value is None:
            return None

        if isinstance(value, (pd.Timestamp, datetime)):
            return value.isoformat()

        if pd.isna(value):
            return None

        if hasattr(value, "item"):
            return value.item()

        return value

    def _build_detail_records(
        self,
        period_df,
        reference_date,
        period_type
    ):

        if period_df.empty:
            return []

        missing_columns = [
            column
            for column in self.DETAIL_COLUMNS
            if column not in period_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Colunas ausentes para a mart detalhada: "
                + ", ".join(missing_columns)
            )

        updated_at = datetime.now().isoformat()
        records = []

        for row in period_df[
            self.DETAIL_COLUMNS
        ].to_dict(orient="records"):

            record = {
                "reference_date": reference_date,
                "period_type": period_type,
                "updated_at": updated_at,
            }

            for key, value in row.items():
                record[key] = self._serialize_value(value)

            records.append(record)

        return records

    def _build_overview_record(
        self,
        overview,
        reference_date,
        period_type
    ):

        top_product = overview.get(
            "top_product"
        )

        return {
            "reference_date": reference_date,
            "period_type": period_type,

            "faturamento_analisavel": (
                overview[
                    "faturamento_analisavel"
                ]
            ),
            "custo_analisavel": (
                overview[
                    "custo_analisavel"
                ]
            ),
            "lucro_bruto": overview[
                "lucro_bruto"
            ],

            "margem_percentual": overview[
                "margem_percentual"
            ],
            "markup_percentual": overview[
                "markup_percentual"
            ],

            "pedidos": overview["pedidos"],
            "produtos": overview["produtos"],
            "clientes": overview["clientes"],
            "vendedores": overview[
                "vendedores"
            ],
            "empresas": overview["empresas"],
            "quantidade": overview[
                "quantidade"
            ],

            "ticket_medio": overview[
                "ticket_medio"
            ],
            "ticket_lucro": overview[
                "ticket_lucro"
            ],

            "produtos_rentaveis": overview[
                "produtos_rentaveis"
            ],
            "produtos_prejuizo": overview[
                "produtos_prejuizo"
            ],
            "produtos_margem_critica": (
                overview[
                    "produtos_margem_critica"
                ]
            ),
            "produtos_margem_baixa": (
                overview[
                    "produtos_margem_baixa"
                ]
            ),

            "faturamento_margem_critica": (
                overview[
                    "faturamento_margem_critica"
                ]
            ),
            "faturamento_produtos_prejuizo": (
                overview[
                    "faturamento_produtos_prejuizo"
                ]
            ),
            "prejuizo_bruto_total": overview[
                "prejuizo_bruto_total"
            ],

            "participacao_faturamento_critico": (
                overview[
                    "participacao_faturamento_critico"
                ]
            ),
            "participacao_faturamento_prejuizo": (
                overview[
                    "participacao_faturamento_prejuizo"
                ]
            ),
            "impacto_prejuizo_sobre_faturamento": (
                overview[
                    "impacto_prejuizo_sobre_faturamento"
                ]
            ),

            "cobertura_financeira": overview[
                "cobertura_financeira"
            ],

            "linhas_total": overview[
                "linhas_total"
            ],
            "linhas_analisaveis": overview[
                "linhas_analisaveis"
            ],
            "linhas_sem_custo": overview[
                "linhas_sem_custo"
            ],
            "linhas_suspeitas": overview[
                "linhas_suspeitas"
            ],
            "linhas_fora_escopo": overview[
                "linhas_fora_escopo"
            ],

            "top_product": top_product,
            "headline": overview["headline"],
            "status": overview["status"],
            "methodology_note": (
                self.METHODOLOGY_NOTE
            ),
            "updated_at": (
                datetime.now().isoformat()
            ),
        }

    def _build_dimension_records(
        self,
        dimensions,
        reference_date,
        period_type
    ):

        records = []

        for dimension_type, items in (
            dimensions.items()
        ):

            for item in items:

                records.append({
                    "reference_date": (
                        reference_date
                    ),
                    "period_type": period_type,
                    "dimension_type": (
                        dimension_type
                    ),
                    "dimension_key": item[
                        "dimension_key"
                    ],
                    "dimension_value": item[
                        "dimension_value"
                    ],
                    "dimension_data": item[
                        "dimension_data"
                    ],

                    "faturamento": item[
                        "faturamento"
                    ],
                    "custo": item["custo"],
                    "lucro": item["lucro"],

                    "margem_percentual": item[
                        "margem_percentual"
                    ],
                    "markup_percentual": item[
                        "markup_percentual"
                    ],

                    "quantidade": item[
                        "quantidade"
                    ],
                    "pedidos": item["pedidos"],
                    "clientes": item["clientes"],
                    "produtos": item["produtos"],
                    "vendedores": item[
                        "vendedores"
                    ],

                    "ticket_medio": item[
                        "ticket_medio"
                    ],
                    "ticket_lucro": item[
                        "ticket_lucro"
                    ],

                    "participacao_faturamento": (
                        item[
                            "participacao_faturamento"
                        ]
                    ),
                    "participacao_lucro": item[
                        "participacao_lucro"
                    ],

                    "data_primeira_venda": item[
                        "data_primeira_venda"
                    ],
                    "data_ultima_venda": item[
                        "data_ultima_venda"
                    ],

                    "status": item["status"],
                    "updated_at": (
                        datetime.now().isoformat()
                    ),
                })

        return records

    def _build_risk_records(
        self,
        risks,
        reference_date,
        period_type
    ):

        records = []

        for risk in risks:

            records.append({
                "reference_date": (
                    reference_date
                ),
                "period_type": period_type,

                "risk_type": risk[
                    "risk_type"
                ],

                "dimension_type": risk[
                    "dimension_type"
                ],
                "dimension_key": risk[
                    "dimension_key"
                ],
                "dimension_value": risk[
                    "dimension_value"
                ],

                "priority": risk["priority"],

                "faturamento": round(
                    self._safe_float(
                        risk.get("faturamento")
                    ),
                    2
                ),
                "lucro": round(
                    self._safe_float(
                        risk.get("lucro")
                    ),
                    2
                ),
                "margem_percentual": (
                    None
                    if risk.get(
                        "margem_percentual"
                    ) is None
                    else round(
                        self._safe_float(
                            risk.get(
                                "margem_percentual"
                            )
                        ),
                        4
                    )
                ),

                "description": risk[
                    "description"
                ],
                "recommended_action": risk[
                    "recommended_action"
                ],
                "updated_at": (
                    datetime.now().isoformat()
                ),
            })

        return records

    def _build_recommendation_records(
        self,
        recommendations,
        reference_date,
        period_type
    ):

        records = []

        for index, item in enumerate(
            recommendations,
            start=1
        ):

            evidence = item.get(
                "evidence_value"
            )

            records.append({
                "reference_date": (
                    reference_date
                ),
                "period_type": period_type,

                "recommendation_type": (
                    item[
                        "recommendation_type"
                    ]
                ),
                "priority": item["priority"],

                "dimension_type": item[
                    "dimension_type"
                ],
                "dimension_key": item[
                    "dimension_key"
                ],
                "dimension_value": item[
                    "dimension_value"
                ],

                "evidence_value": (
                    None
                    if evidence is None
                    else round(
                        self._safe_float(
                            evidence
                        ),
                        6
                    )
                ),

                "title": item["title"],
                "description": item[
                    "description"
                ],
                "action": item["action"],
                "sort_order": index,
                "updated_at": (
                    datetime.now().isoformat()
                ),
            })

        return records

    def _build_quality_records(
        self,
        quality,
        reference_date,
        period_type
    ):

        records = []

        for item in quality:

            records.append({
                "reference_date": (
                    reference_date
                ),
                "period_type": period_type,

                "analysis_status": item[
                    "analysis_status"
                ],

                "linhas": item["linhas"],
                "pedidos": item["pedidos"],
                "produtos": item["produtos"],
                "clientes": item["clientes"],

                "faturamento": item[
                    "faturamento"
                ],
                "participacao_faturamento": (
                    item[
                        "participacao_faturamento"
                    ]
                ),

                "description": item[
                    "description"
                ],
                "updated_at": (
                    datetime.now().isoformat()
                ),
            })

        return records

    def _save_period(
        self,
        reference_date,
        period_type,
        overview_record,
        detail_records,
        dimension_records,
        risk_records,
        recommendation_records,
        quality_records
    ):

        filters = {
            "reference_date": reference_date,
            "period_type": period_type,
        }

        self.supabase.replace_snapshot(
            "mart_profitability_overview",
            filters,
            [overview_record]
        )

        self.supabase.replace_snapshot_batches(
            "mart_profitability_detail_snapshot",
            filters,
            detail_records,
            batch_size=500
        )

        self.supabase.replace_snapshot_batches(
            "mart_profitability_dimension_snapshot",
            filters,
            dimension_records,
            batch_size=500
        )

        self.supabase.replace_snapshot_batches(
            "mart_profitability_risk",
            filters,
            risk_records,
            batch_size=500
        )

        self.supabase.replace_snapshot(
            "mart_profitability_recommendation",
            filters,
            recommendation_records
        )

        self.supabase.replace_snapshot(
            "mart_profitability_quality_snapshot",
            filters,
            quality_records
        )

    def run(self):

        today = datetime.today().date()
        reference_date = today.isoformat()

        orders_raw = PedidoExtractor(
            self.sql_connector
        ).extract()

        products_raw = ProdutoExtractor(
            self.sql_connector
        ).extract()

        orders = (
            PedidoTransformer()
            .filter_revenue_orders(
                orders_raw
            )
        )

        products = (
            ProdutoTransformer()
            .prepare(
                products_raw
            )
        )

        dataset = (
            ProfitabilityDataset()
            .build(
                orders,
                products
            )
        )

        dataset = dataset[
            dataset["data_venda"].notna()
        ].copy()

        overview_builder = (
            ProfitabilityOverview()
        )
        dimensions_builder = (
            ProfitabilityDimensions()
        )
        risk_builder = ProfitabilityRisk()
        recommendation_builder = (
            ProfitabilityRecommendations()
        )
        quality_builder = (
            ProfitabilityQuality()
        )

        periods_to_generate = (
            ["historico"]
            + list(MVP_PERIODS)
        )

        period_results = {}

        for period_type in periods_to_generate:

            if period_type == "historico":

                period_df = dataset.copy()

                if period_df.empty:
                    date_from = today
                    date_to = today
                else:
                    date_from = (
                        period_df[
                            "data_venda"
                        ].min().date()
                    )
                    date_to = (
                        period_df[
                            "data_venda"
                        ].max().date()
                    )

            else:

                window = resolve_window(
                    period_type,
                    today
                )

                period_df = dataset[
                    (
                        dataset[
                            "data_venda"
                        ].dt.date
                        >= window.date_from
                    )
                    & (
                        dataset[
                            "data_venda"
                        ].dt.date
                        <= window.date_to
                    )
                ].copy()

                date_from = window.date_from
                date_to = window.date_to

            print(
                "  Gerando marts de rentabilidade: "
                f"{period_type} "
                f"({date_from} até {date_to}) "
                f"- {len(period_df)} registros"
            )

            overview = (
                overview_builder.build(
                    period_df
                )
            )

            dimensions = (
                dimensions_builder.build(
                    period_df
                )
            )

            risks = risk_builder.build(
                dimensions,
                overview
            )

            recommendations = (
                recommendation_builder.build(
                    dimensions,
                    overview,
                    risks
                )
            )

            quality = quality_builder.build(
                period_df
            )

            overview_record = (
                self._build_overview_record(
                    overview,
                    reference_date,
                    period_type
                )
            )

            detail_records = (
                self._build_detail_records(
                    period_df,
                    reference_date,
                    period_type
                )
            )

            dimension_records = (
                self._build_dimension_records(
                    dimensions,
                    reference_date,
                    period_type
                )
            )

            risk_records = (
                self._build_risk_records(
                    risks,
                    reference_date,
                    period_type
                )
            )

            recommendation_records = (
                self._build_recommendation_records(
                    recommendations,
                    reference_date,
                    period_type
                )
            )

            quality_records = (
                self._build_quality_records(
                    quality,
                    reference_date,
                    period_type
                )
            )

            self._save_period(
                reference_date=reference_date,
                period_type=period_type,
                overview_record=overview_record,
                detail_records=detail_records,
                dimension_records=dimension_records,
                risk_records=risk_records,
                recommendation_records=(
                    recommendation_records
                ),
                quality_records=quality_records
            )

            period_results[period_type] = {
                "source_rows": len(period_df),
                "detail_rows": len(detail_records),
                "analyzable_rows": overview[
                    "linhas_analisaveis"
                ],
                "dimensions": len(
                    dimension_records
                ),
                "risks": len(risk_records),
                "recommendations": len(
                    recommendation_records
                ),
                "quality": len(
                    quality_records
                ),
                "revenue": overview[
                    "faturamento_analisavel"
                ],
                "profit": overview[
                    "lucro_bruto"
                ],
                "margin": overview[
                    "margem_percentual"
                ],
                "markup": overview[
                    "markup_percentual"
                ],
                "coverage": overview[
                    "cobertura_financeira"
                ],
                "status": overview["status"],
            }

        ytd_result = period_results.get(
            "ytd",
            {}
        )

        return {
            "periods_generated": len(
                period_results
            ),
            "period_results": (
                period_results
            ),
            "ytd_source_rows": (
                ytd_result.get(
                    "source_rows",
                    0
                )
            ),
            "ytd_detail_rows": (
                ytd_result.get(
                    "detail_rows",
                    0
                )
            ),
            "ytd_analyzable_rows": (
                ytd_result.get(
                    "analyzable_rows",
                    0
                )
            ),
            "ytd_dimensions": (
                ytd_result.get(
                    "dimensions",
                    0
                )
            ),
            "ytd_risks": ytd_result.get(
                "risks",
                0
            ),
            "ytd_recommendations": (
                ytd_result.get(
                    "recommendations",
                    0
                )
            ),
            "ytd_revenue": ytd_result.get(
                "revenue",
                0
            ),
            "ytd_profit": ytd_result.get(
                "profit",
                0
            ),
            "ytd_margin": ytd_result.get(
                "margin",
                0
            ),
            "ytd_markup": ytd_result.get(
                "markup",
                0
            ),
            "ytd_coverage": ytd_result.get(
                "coverage",
                0
            ),
            "ytd_status": ytd_result.get(
                "status",
                "unknown"
            ),
        }