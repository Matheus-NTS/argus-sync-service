from features.intelligence.stock.stock_policy import (
    CURVE_COVERAGE_MONTHS,
    DEFAULT_CURVE_COVERAGE_MONTHS,
    DEMAND_WINDOW_MONTHS,
    LEAD_TIME_MAX_MONTHS,
    SCENARIO_MONTHS,
    OFFICIAL_TARGET_MONTHS,
    EXCESS_COVERAGE_MONTHS,
)
from datetime import datetime

import math
import pandas as pd

from features.intelligence.stock.stock_policy import (
    CURVE_COVERAGE_MONTHS,
    DEFAULT_CURVE_COVERAGE_MONTHS,
    DEMAND_WINDOW_MONTHS,
    LEAD_TIME_MAX_MONTHS,
    SCENARIO_MONTHS,
)


class StockConsolidated:

    @staticmethod
    def _first_not_null(series):
        values = series.dropna()

        if len(values) == 0:
            return None

        return values.iloc[0]

    @staticmethod
    def _normalize_curve(value):
        if pd.isna(value):
            return None

        curva = str(value).strip().upper()

        return curva or None

    @staticmethod
    def _coverage_factor(curva):
        curva = StockConsolidated._normalize_curve(
            curva
        )

        return CURVE_COVERAGE_MONTHS.get(
            curva,
            DEFAULT_CURVE_COVERAGE_MONTHS,
        )

    def build(self, stock_df):

        if (
            stock_df is None
            or len(stock_df) == 0
        ):
            return pd.DataFrame()

        base = stock_df.copy()

        # ---------------------------------------------------------
        # Política ABCDE por posição/empresa
        # ---------------------------------------------------------
        # A curva continua sendo a curva oficial recebida do ERP.
        # Não é criada uma curva consolidada artificial.

        base["_demanda_mensal_policy"] = (
            base["qtd_vendida_180d"]
            / DEMAND_WINDOW_MONTHS
        )

        base["_fator_policy"] = (
            base["Curva_ABCDE"]
            .apply(
                self._coverage_factor
            )
        )

        base["_estoque_policy"] = (
            base["_demanda_mensal_policy"]
            * base["_fator_policy"]
        )

        # ---------------------------------------------------------
        # Agregação dos FATOS
        # ---------------------------------------------------------

        grouped = (
            base
            .groupby(
                "codigo_produto",
                dropna=False,
            )
            .agg(
                produto=(
                    "Descricao",
                    self._first_not_null,
                ),
                codigo_fabricante=(
                    "Codigo_Fabricante",
                    self._first_not_null,
                ),
                fabricante=(
                    "Fabricante",
                    self._first_not_null,
                ),
                classificacao_produto=(
                    "Classificacao_Produto",
                    self._first_not_null,
                ),
                estoque_atual=(
                    "Quantidade_Estoque",
                    "sum",
                ),
                valor_estoque=(
                    "valor_estoque",
                    "sum",
                ),
                qtd_vendida_30d=(
                    "qtd_vendida_30d",
                    "sum",
                ),
                faturamento_30d=(
                    "faturamento_30d",
                    "sum",
                ),
                qtd_vendida_90d=(
                    "qtd_vendida_90d",
                    "sum",
                ),
                faturamento_90d=(
                    "faturamento_90d",
                    "sum",
                ),
                qtd_vendida_180d=(
                    "qtd_vendida_180d",
                    "sum",
                ),
                faturamento_180d=(
                    "faturamento_180d",
                    "sum",
                ),
                ultima_venda=(
                    "ultima_venda",
                    "max",
                ),
                posicoes_estoque=(
                    "Empresa",
                    "size",
                ),
                empresas_com_produto=(
                    "Empresa",
                    "nunique",
                ),
                estoque_politica_curvas=(
                    "_estoque_policy",
                    "sum",
                ),
            )
            .reset_index()
        )

        # ---------------------------------------------------------
        # Curvas oficiais existentes nas empresas
        # ---------------------------------------------------------

        curves = (
            base
            .assign(
                _curva=base[
                    "Curva_ABCDE"
                ].apply(
                    self._normalize_curve
                )
            )
            .groupby(
                "codigo_produto",
                dropna=False,
            )["_curva"]
            .apply(
                lambda values: "|".join(
                    sorted(
                        {
                            value
                            for value
                            in values
                            if value
                        }
                    )
                )
            )
            .rename(
                "curvas_origem"
            )
            .reset_index()
        )

        grouped = grouped.merge(
            curves,
            on="codigo_produto",
            how="left",
        )

        # ---------------------------------------------------------
        # Demanda consolidada
        # ---------------------------------------------------------

        grouped["demanda_mensal_6m"] = (
            grouped[
                "qtd_vendida_180d"
            ]
            / DEMAND_WINDOW_MONTHS
        )

        # ---------------------------------------------------------
        # Cobertura consolidada
        # ---------------------------------------------------------

        grouped["cobertura_estoque"] = (
            grouped.apply(
                lambda row: (
                    row["estoque_atual"]
                    / row[
                        "demanda_mensal_6m"
                    ]
                    if row[
                        "demanda_mensal_6m"
                    ] > 0
                    else None
                ),
                axis=1,
            )
        )

        # ---------------------------------------------------------
        # Dias para esgotar
        # ---------------------------------------------------------

        grouped["dias_para_esgotar"] = (
            grouped.apply(
                lambda row: (
                    round(
                        (
                            row[
                                "estoque_atual"
                            ]
                            / row[
                                "demanda_mensal_6m"
                            ]
                        )
                        * 30,
                        0,
                    )
                    if row[
                        "demanda_mensal_6m"
                    ] > 0
                    else None
                ),
                axis=1,
            )
        )

        hoje = datetime.today().date()

        grouped["dias_sem_venda"] = (
            grouped[
                "ultima_venda"
            ].apply(
                lambda value: (
                    (
                        pd.Timestamp(hoje)
                        - value
                    ).days
                    if pd.notnull(value)
                    else None
                )
            )
        )

        # ---------------------------------------------------------
        # Lead time
        # ---------------------------------------------------------

        grouped[
            "ponto_pedido_lead_time"
        ] = (
            grouped[
                "demanda_mensal_6m"
            ]
            * LEAD_TIME_MAX_MONTHS
        )

        # ---------------------------------------------------------
        # Política ABCDE consolidada
        # ---------------------------------------------------------
        # Não é soma de KPI arbitrário.
        #
        # É a soma das necessidades calculadas a partir da demanda
        # factual de cada empresa e da curva oficial recebida do ERP.

        grouped[
            "sugestao_politica_curvas"
        ] = (
            grouped[
                "estoque_politica_curvas"
            ]
            - grouped["estoque_atual"]
        ).clip(
            lower=0
        ).apply(
            math.ceil
        )

        # ---------------------------------------------------------
        # Cenários executivos
        # ---------------------------------------------------------

        for meses in SCENARIO_MONTHS:

            estoque_col = (
                f"estoque_cenario_{meses}m"
            )

            sugestao_col = (
                f"sugestao_cenario_{meses}m"
            )

            grouped[estoque_col] = (
                grouped[
                    "demanda_mensal_6m"
                ]
                * meses
            )

            grouped[sugestao_col] = (
                grouped[estoque_col]
                - grouped[
                    "estoque_atual"
                ]
            ).clip(
                lower=0
            ).apply(
                math.ceil
            )

                    # ---------------------------------------------------------
        # Reposição V2 consolidada
        # ---------------------------------------------------------

        def classify_replenishment(row):

            demanda = row["demanda_mensal_6m"]
            cobertura = row["cobertura_estoque"]
            estoque = row["estoque_atual"]

            if demanda <= 0:
                return "sem_demanda"

            if estoque <= 0:
                return "comprar_agora"

            if (
                cobertura is not None
                and cobertura <= LEAD_TIME_MAX_MONTHS
            ):
                return "comprar_agora"

            if (
                cobertura is not None
                and cobertura < OFFICIAL_TARGET_MONTHS
            ):
                return "atencao"

            if (
                cobertura is not None
                and cobertura > EXCESS_COVERAGE_MONTHS
            ):
                return "excesso"

            return "saudavel"

        grouped["replenishment_status"] = (
            grouped.apply(
                classify_replenishment,
                axis=1,
            )
        )

        action_mapping = {
            "comprar_agora": "Comprar agora",
            "atencao": "Planejar reposição",
            "saudavel": "Sem ação imediata",
            "excesso": "Revisar excesso / capital parado",
            "sem_demanda": "Sem demanda recente",
        }

        grouped["replenishment_action"] = (
            grouped["replenishment_status"]
            .map(action_mapping)
        )

        # ---------------------------------------------------------
        # Risco V2 consolidado
        # ---------------------------------------------------------

        def classify_risk(row):

            estoque = row["estoque_atual"]
            demanda_180 = row["qtd_vendida_180d"]
            cobertura = row["cobertura_estoque"]
            dias_sem_venda = row["dias_sem_venda"]

            if (
                estoque <= 0
                and demanda_180 > 0
            ):
                return "ruptura"

            if (
                estoque > 0
                and dias_sem_venda is not None
                and dias_sem_venda >= 60
            ):
                return "sem_giro"

            if (
                cobertura is not None
                and cobertura > EXCESS_COVERAGE_MONTHS
            ):
                return "excesso"

            return "normal"

        grouped["risk_type"] = (
            grouped.apply(
                classify_risk,
                axis=1,
            )
        )

        # ---------------------------------------------------------
        # Status executivo V2
        # ---------------------------------------------------------

        def classify_status(row):

            risk_type = row["risk_type"]
            replenishment = row[
                "replenishment_status"
            ]

            if risk_type == "ruptura":
                return "critical"

            if replenishment == "comprar_agora":
                return "critical"

            if risk_type in {
                "sem_giro",
                "excesso",
            }:
                return "attention"

            if replenishment in {
                "atencao",
                "excesso",
            }:
                return "attention"

            return "healthy"

        grouped["status"] = (
            grouped.apply(
                classify_status,
                axis=1,
            )
        )

        return grouped