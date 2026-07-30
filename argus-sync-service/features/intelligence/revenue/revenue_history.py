import numpy as np
import pandas as pd

from features.shared.commercial_dimensions import (
    CommercialDimensions,
)


class RevenueHistory:
    """
    Constrói as bases históricas de faturamento do ARGUS.

    Bases geradas:
    - histórico mensal consolidado;
    - histórico anual consolidado;
    - histórico YTD;
    - histórico mensal por empresa;
    - histórico mensal por empresa e vendedor;
    - resumo histórico consolidado e por empresa.

    Observações:
    - o mesmo número de pedido pode existir em empresas diferentes;
    - o mesmo vendedor pode existir em empresas diferentes;
    - por isso, pedidos e vendedores utilizam chaves compostas;
    - empresa e vendedor são normalizados pelas dimensões
      comerciais compartilhadas do ARGUS.
    """

    MONTH_NAMES = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }

    REQUIRED_COLUMNS = [
        "Data",
        "ano",
        "mes",
        "ano_mes",
        "Empresa",
        "Vendedor",
        "numero_pedido",
        "Valor_total_Unitario",
    ]

    def build(
        self,
        revenue_df: pd.DataFrame,
    ) -> dict[str, pd.DataFrame]:
        """
        Gera todas as visões históricas de faturamento.
        """
        revenue = self._prepare_dataframe(
            revenue_df
        )

        monthly = self.build_monthly(
            revenue
        )

        yearly = self.build_yearly(
            monthly
        )

        ytd = self.build_ytd(
            monthly
        )

        company_monthly = (
            self.build_company_monthly(
                revenue=revenue,
                monthly=monthly,
            )
        )

        seller_monthly = (
            self.build_seller_monthly(
                revenue=revenue,
                company_monthly=company_monthly,
            )
        )

        historical_summary = (
            self.build_historical_summary(
                revenue
            )
        )

        return {
            "monthly": monthly,
            "yearly": yearly,
            "ytd": ytd,
            "company_monthly": company_monthly,
            "seller_monthly": seller_monthly,
            "historical_summary": historical_summary,
        }

    def build_monthly(
        self,
        revenue_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Gera o histórico mensal consolidado.

        Todos os meses de cada ano disponível são incluídos.
        Meses sem movimento recebem faturamento e pedidos
        iguais a zero.
        """
        revenue = self._prepare_dataframe(
            revenue_df
        )

        monthly_revenue = (
            revenue
            .groupby(
                [
                    "ano",
                    "mes",
                    "ano_mes",
                ],
                as_index=False,
            )
            .agg(
                faturamento=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                pedidos=(
                    "pedido_chave",
                    "nunique",
                ),
                empresas_ativas=(
                    "Empresa",
                    "nunique",
                ),
                vendedores_ativos=(
                    "vendedor_chave",
                    "nunique",
                ),
            )
        )

        calendar = self._build_month_calendar(
            revenue
        )

        monthly = calendar.merge(
            monthly_revenue,
            on=[
                "ano",
                "mes",
                "ano_mes",
            ],
            how="left",
        )

        numeric_fill_columns = [
            "faturamento",
            "pedidos",
            "empresas_ativas",
            "vendedores_ativos",
        ]

        monthly[numeric_fill_columns] = (
            monthly[numeric_fill_columns]
            .fillna(0)
        )

        monthly["faturamento"] = (
            monthly["faturamento"]
            .astype(float)
            .round(2)
        )

        for column in [
            "pedidos",
            "empresas_ativas",
            "vendedores_ativos",
        ]:
            monthly[column] = (
                monthly[column]
                .astype(int)
            )

        monthly["ticket_medio"] = np.where(
            monthly["pedidos"] > 0,
            (
                monthly["faturamento"]
                / monthly["pedidos"]
            ),
            0.0,
        )

        monthly["tem_movimento"] = (
            monthly["pedidos"] > 0
        )

        monthly = monthly.sort_values(
            [
                "ano",
                "mes",
            ]
        ).reset_index(
            drop=True
        )

        last_data = pd.to_datetime(
            revenue["Data"],
            errors="coerce",
        ).max()

        last_year = int(
            last_data.year
        )

        last_month = int(
            last_data.month
        )

        monthly["periodo_futuro"] = (
            (monthly["ano"] > last_year)
            |
            (
                (monthly["ano"] == last_year)
                & (monthly["mes"] > last_month)
            )
        )

        monthly["mes_em_aberto"] = (
            (monthly["ano"] == last_year)
            & (monthly["mes"] == last_month)
        )

        monthly["faturamento_mes_anterior"] = (
            monthly["faturamento"]
            .shift(1)
        )

        monthly["crescimento_mom"] = (
            self._calculate_growth(
                current=monthly["faturamento"],
                previous=monthly[
                    "faturamento_mes_anterior"
                ],
            )
        )

        previous_year = monthly[
            [
                "ano",
                "mes",
                "faturamento",
            ]
        ].copy()

        previous_year["ano"] = (
            previous_year["ano"] + 1
        )

        previous_year = previous_year.rename(
            columns={
                "faturamento":
                    "faturamento_ano_anterior",
            }
        )

        monthly = monthly.merge(
            previous_year,
            on=[
                "ano",
                "mes",
            ],
            how="left",
        )

        monthly["crescimento_yoy"] = (
            self._calculate_growth(
                current=monthly["faturamento"],
                previous=monthly[
                    "faturamento_ano_anterior"
                ],
            )
        )

        monthly.loc[
            monthly["periodo_futuro"],
            [
                "faturamento_mes_anterior",
                "crescimento_mom",
                "faturamento_ano_anterior",
                "crescimento_yoy",
            ],
        ] = np.nan

        monthly["acumulado_ytd"] = (
            monthly
            .groupby("ano")["faturamento"]
            .cumsum()
            .round(2)
        )

        monthly["mes_nome"] = (
            monthly["mes"]
            .map(self.MONTH_NAMES)
        )

        monthly["trimestre"] = (
            ((monthly["mes"] - 1) // 3) + 1
        )

        monthly["semestre"] = np.where(
            monthly["mes"] <= 6,
            1,
            2,
        )

        monetary_columns = [
            "faturamento",
            "ticket_medio",
            "faturamento_mes_anterior",
            "faturamento_ano_anterior",
            "acumulado_ytd",
        ]

        monthly[monetary_columns] = (
            monthly[monetary_columns]
            .round(2)
        )

        percentage_columns = [
            "crescimento_mom",
            "crescimento_yoy",
        ]

        monthly[percentage_columns] = (
            monthly[percentage_columns]
            .round(6)
        )

        ordered_columns = [
            "ano",
            "mes",
            "mes_nome",
            "ano_mes",
            "trimestre",
            "semestre",
            "faturamento",
            "pedidos",
            "ticket_medio",
            "empresas_ativas",
            "vendedores_ativos",
            "tem_movimento",
            "periodo_futuro",
            "mes_em_aberto",
            "faturamento_mes_anterior",
            "crescimento_mom",
            "faturamento_ano_anterior",
            "crescimento_yoy",
            "acumulado_ytd",
        ]

        return monthly[
            ordered_columns
        ].copy()

    def build_yearly(
        self,
        monthly_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Gera o histórico anual a partir do histórico mensal.
        """
        if (
            monthly_df is None
            or monthly_df.empty
        ):
            raise ValueError(
                "O histórico mensal está vazio."
            )

        active_months = monthly_df[
            monthly_df["tem_movimento"]
        ].copy()

        yearly = (
            monthly_df
            .groupby(
                "ano",
                as_index=False,
            )
            .agg(
                faturamento=(
                    "faturamento",
                    "sum",
                ),
                pedidos=(
                    "pedidos",
                    "sum",
                ),
                meses_com_movimento=(
                    "tem_movimento",
                    "sum",
                ),
            )
        )

        yearly["ticket_medio"] = np.where(
            yearly["pedidos"] > 0,
            (
                yearly["faturamento"]
                / yearly["pedidos"]
            ),
            0.0,
        )

        yearly["media_mensal"] = np.where(
            yearly["meses_com_movimento"] > 0,
            (
                yearly["faturamento"]
                / yearly["meses_com_movimento"]
            ),
            0.0,
        )

        best_month = (
            active_months
            .sort_values(
                [
                    "ano",
                    "faturamento",
                    "mes",
                ],
                ascending=[
                    True,
                    False,
                    True,
                ],
            )
            .drop_duplicates(
                subset=["ano"],
                keep="first",
            )
            [
                [
                    "ano",
                    "mes",
                    "mes_nome",
                    "faturamento",
                ]
            ]
            .rename(
                columns={
                    "mes":
                        "melhor_mes",
                    "mes_nome":
                        "melhor_mes_nome",
                    "faturamento":
                        "melhor_mes_faturamento",
                }
            )
        )

        worst_month = (
            active_months
            .sort_values(
                [
                    "ano",
                    "faturamento",
                    "mes",
                ],
                ascending=[
                    True,
                    True,
                    True,
                ],
            )
            .drop_duplicates(
                subset=["ano"],
                keep="first",
            )
            [
                [
                    "ano",
                    "mes",
                    "mes_nome",
                    "faturamento",
                ]
            ]
            .rename(
                columns={
                    "mes":
                        "pior_mes",
                    "mes_nome":
                        "pior_mes_nome",
                    "faturamento":
                        "pior_mes_faturamento",
                }
            )
        )

        yearly = yearly.merge(
            best_month,
            on="ano",
            how="left",
        )

        yearly = yearly.merge(
            worst_month,
            on="ano",
            how="left",
        )

        yearly = yearly.sort_values(
            "ano"
        ).reset_index(
            drop=True
        )

        yearly["ano_completo"] = (
            yearly["meses_com_movimento"] == 12
        )

        yearly["faturamento_ano_anterior"] = (
            yearly["faturamento"]
            .shift(1)
        )

        yearly["ano_anterior_completo"] = (
            yearly["ano_completo"]
            .shift(1)
        )

        valid_annual_comparison = (
            yearly["ano_completo"]
            & yearly[
                "ano_anterior_completo"
            ].fillna(False)
            & yearly[
                "faturamento_ano_anterior"
            ].notna()
            & (
                yearly[
                    "faturamento_ano_anterior"
                ] != 0
            )
        )

        yearly["crescimento_anual"] = np.where(
            valid_annual_comparison,
            (
                yearly["faturamento"]
                - yearly[
                    "faturamento_ano_anterior"
                ]
            )
            / yearly[
                "faturamento_ano_anterior"
            ],
            np.nan,
        )

        monetary_columns = [
            "faturamento",
            "ticket_medio",
            "media_mensal",
            "melhor_mes_faturamento",
            "pior_mes_faturamento",
            "faturamento_ano_anterior",
        ]

        yearly[monetary_columns] = (
            yearly[monetary_columns]
            .round(2)
        )

        yearly["crescimento_anual"] = (
            yearly["crescimento_anual"]
            .round(6)
        )

        yearly["meses_com_movimento"] = (
            yearly["meses_com_movimento"]
            .astype(int)
        )

        return yearly

    def build_ytd(
        self,
        monthly_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compara os anos utilizando o mesmo intervalo de meses.
        """
        if (
            monthly_df is None
            or monthly_df.empty
        ):
            raise ValueError(
                "O histórico mensal está vazio."
            )

        latest_year = int(
            monthly_df["ano"].max()
        )

        latest_year_data = monthly_df[
            (monthly_df["ano"] == latest_year)
            & monthly_df["tem_movimento"]
        ]

        if latest_year_data.empty:
            raise ValueError(
                "O ano mais recente não possui movimento."
            )

        comparison_month = int(
            latest_year_data["mes"].max()
        )

        ytd = (
            monthly_df[
                (
                    monthly_df["mes"]
                    <= comparison_month
                )
                & (
                    ~monthly_df["periodo_futuro"]
                )
            ]
            .groupby(
                "ano",
                as_index=False,
            )
            .agg(
                faturamento_ytd=(
                    "faturamento",
                    "sum",
                ),
                pedidos_ytd=(
                    "pedidos",
                    "sum",
                ),
            )
            .sort_values("ano")
            .reset_index(
                drop=True
            )
        )

        ytd["mes_limite"] = (
            comparison_month
        )

        ytd["faturamento_ytd_ano_anterior"] = (
            ytd["faturamento_ytd"]
            .shift(1)
        )

        ytd["crescimento_ytd"] = (
            self._calculate_growth(
                current=ytd[
                    "faturamento_ytd"
                ],
                previous=ytd[
                    "faturamento_ytd_ano_anterior"
                ],
            )
        )

        ytd[
            [
                "faturamento_ytd",
                "faturamento_ytd_ano_anterior",
            ]
        ] = (
            ytd[
                [
                    "faturamento_ytd",
                    "faturamento_ytd_ano_anterior",
                ]
            ]
            .round(2)
        )

        ytd["crescimento_ytd"] = (
            ytd["crescimento_ytd"]
            .round(6)
        )

        return ytd

    def build_company_monthly(
        self,
        revenue: pd.DataFrame,
        monthly: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Gera o histórico mensal por empresa.
        """
        company_monthly = (
            revenue
            .groupby(
                [
                    "ano",
                    "mes",
                    "ano_mes",
                    "Empresa",
                ],
                as_index=False,
            )
            .agg(
                faturamento=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                pedidos=(
                    "pedido_chave",
                    "nunique",
                ),
                vendedores_ativos=(
                    "vendedor_chave",
                    "nunique",
                ),
            )
        )

        company_monthly["ticket_medio"] = np.where(
            company_monthly["pedidos"] > 0,
            (
                company_monthly["faturamento"]
                / company_monthly["pedidos"]
            ),
            0.0,
        )

        monthly_total = monthly[
            [
                "ano",
                "mes",
                "faturamento",
            ]
        ].rename(
            columns={
                "faturamento":
                    "faturamento_total_mes",
            }
        )

        company_monthly = (
            company_monthly.merge(
                monthly_total,
                on=[
                    "ano",
                    "mes",
                ],
                how="left",
            )
        )

        company_monthly[
            "participacao_mensal"
        ] = np.where(
            company_monthly[
                "faturamento_total_mes"
            ] != 0,
            (
                company_monthly["faturamento"]
                / company_monthly[
                    "faturamento_total_mes"
                ]
            ),
            0.0,
        )

        company_monthly = (
            company_monthly.sort_values(
                [
                    "ano",
                    "mes",
                    "faturamento",
                ],
                ascending=[
                    True,
                    True,
                    False,
                ],
            )
            .reset_index(
                drop=True
            )
        )

        company_monthly[
            "ranking_empresa_mes"
        ] = (
            company_monthly
            .groupby(
                [
                    "ano",
                    "mes",
                ]
            )["faturamento"]
            .rank(
                method="dense",
                ascending=False,
            )
            .astype(int)
        )

        company_monthly[
            [
                "faturamento",
                "ticket_medio",
                "faturamento_total_mes",
            ]
        ] = (
            company_monthly[
                [
                    "faturamento",
                    "ticket_medio",
                    "faturamento_total_mes",
                ]
            ]
            .round(2)
        )

        company_monthly[
            "participacao_mensal"
        ] = (
            company_monthly[
                "participacao_mensal"
            ]
            .round(6)
        )

        return company_monthly

    def build_seller_monthly(
        self,
        revenue: pd.DataFrame,
        company_monthly: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Gera o histórico mensal por Empresa + Vendedor.

        A empresa faz parte obrigatória da chave,
        pois o mesmo vendedor pode atuar em empresas distintas.
        """
        seller_monthly = (
            revenue
            .groupby(
                [
                    "ano",
                    "mes",
                    "ano_mes",
                    "Empresa",
                    "Vendedor",
                ],
                as_index=False,
            )
            .agg(
                faturamento=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                pedidos=(
                    "pedido_chave",
                    "nunique",
                ),
            )
        )

        seller_monthly["ticket_medio"] = np.where(
            seller_monthly["pedidos"] > 0,
            (
                seller_monthly["faturamento"]
                / seller_monthly["pedidos"]
            ),
            0.0,
        )

        company_total = company_monthly[
            [
                "ano",
                "mes",
                "Empresa",
                "faturamento",
            ]
        ].rename(
            columns={
                "faturamento":
                    "faturamento_empresa_mes",
            }
        )

        seller_monthly = (
            seller_monthly.merge(
                company_total,
                on=[
                    "ano",
                    "mes",
                    "Empresa",
                ],
                how="left",
            )
        )

        seller_monthly[
            "participacao_empresa"
        ] = np.where(
            seller_monthly[
                "faturamento_empresa_mes"
            ] != 0,
            (
                seller_monthly["faturamento"]
                / seller_monthly[
                    "faturamento_empresa_mes"
                ]
            ),
            0.0,
        )

        seller_monthly = (
            seller_monthly.sort_values(
                [
                    "ano",
                    "mes",
                    "Empresa",
                    "faturamento",
                ],
                ascending=[
                    True,
                    True,
                    True,
                    False,
                ],
            )
            .reset_index(
                drop=True
            )
        )

        seller_monthly[
            "ranking_vendedor_empresa"
        ] = (
            seller_monthly
            .groupby(
                [
                    "ano",
                    "mes",
                    "Empresa",
                ]
            )["faturamento"]
            .rank(
                method="dense",
                ascending=False,
            )
            .astype(int)
        )

        seller_monthly[
            [
                "faturamento",
                "ticket_medio",
                "faturamento_empresa_mes",
            ]
        ] = (
            seller_monthly[
                [
                    "faturamento",
                    "ticket_medio",
                    "faturamento_empresa_mes",
                ]
            ]
            .round(2)
        )

        seller_monthly[
            "participacao_empresa"
        ] = (
            seller_monthly[
                "participacao_empresa"
            ]
            .round(6)
        )

        return seller_monthly

    def build_historical_summary(
        self,
        revenue_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Gera o resumo histórico acumulado do faturamento.

        O contrato contém:
        - uma linha consolidada de toda a operação;
        - uma linha para cada empresa;
        - faturamento, pedidos e ticket médio históricos;
        - primeira e última venda;
        - extensão e cobertura da série;
        - participação e ranking histórico por empresa.

        Regras:
        - pedidos são contados pela chave composta
          Empresa + número do pedido;
        - a participação das empresas usa o faturamento
          consolidado como denominador;
        - o registro consolidado recebe participação 1.0
          e ranking 0, pois não concorre com as empresas.
        """
        revenue = self._prepare_dataframe(
            revenue_df
        )

        if revenue.empty:
            raise ValueError(
                "A base histórica de faturamento está vazia."
            )

        total_revenue = float(
            revenue["Valor_total_Unitario"].sum()
        )

        total_orders = int(
            revenue["pedido_chave"].nunique()
        )

        first_sale = pd.to_datetime(
            revenue["Data"],
            errors="coerce",
        ).min()

        last_sale = pd.to_datetime(
            revenue["Data"],
            errors="coerce",
        ).max()

        consolidated = {
            "empresa": "Consolidado",
            "nivel": "consolidado",
            "faturamento_total": round(
                total_revenue,
                2,
            ),
            "pedidos_total": total_orders,
            "ticket_medio": round(
                (
                    total_revenue / total_orders
                    if total_orders > 0
                    else 0.0
                ),
                2,
            ),
            "primeira_venda": first_sale,
            "ultima_venda": last_sale,
            "dias_historico": int(
                (last_sale - first_sale).days
            ),
            "meses_com_movimento": int(
                revenue["ano_mes"].nunique()
            ),
            "anos_com_movimento": int(
                revenue["ano"].nunique()
            ),
            "primeiro_ano": int(
                revenue["ano"].min()
            ),
            "ultimo_ano": int(
                revenue["ano"].max()
            ),
            "participacao_historica": 1.0,
            "ranking_historico": 0,
        }

        company_summary = (
            revenue
            .groupby(
                "Empresa",
                as_index=False,
                dropna=False,
            )
            .agg(
                faturamento_total=(
                    "Valor_total_Unitario",
                    "sum",
                ),
                pedidos_total=(
                    "pedido_chave",
                    "nunique",
                ),
                primeira_venda=(
                    "Data",
                    "min",
                ),
                ultima_venda=(
                    "Data",
                    "max",
                ),
                meses_com_movimento=(
                    "ano_mes",
                    "nunique",
                ),
                anos_com_movimento=(
                    "ano",
                    "nunique",
                ),
                primeiro_ano=(
                    "ano",
                    "min",
                ),
                ultimo_ano=(
                    "ano",
                    "max",
                ),
            )
            .rename(
                columns={
                    "Empresa": "empresa",
                }
            )
        )

        company_summary["nivel"] = "empresa"

        company_summary["ticket_medio"] = np.where(
            company_summary["pedidos_total"] > 0,
            (
                company_summary["faturamento_total"]
                / company_summary["pedidos_total"]
            ),
            0.0,
        )

        company_summary["dias_historico"] = (
            pd.to_datetime(
                company_summary["ultima_venda"],
                errors="coerce",
            )
            - pd.to_datetime(
                company_summary["primeira_venda"],
                errors="coerce",
            )
        ).dt.days

        company_summary[
            "participacao_historica"
        ] = np.where(
            total_revenue != 0,
            (
                company_summary["faturamento_total"]
                / total_revenue
            ),
            0.0,
        )

        company_summary = (
            company_summary
            .sort_values(
                [
                    "faturamento_total",
                    "empresa",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
            .reset_index(
                drop=True
            )
        )

        company_summary[
            "ranking_historico"
        ] = (
            company_summary[
                "faturamento_total"
            ]
            .rank(
                method="dense",
                ascending=False,
            )
            .astype(int)
        )

        monetary_columns = [
            "faturamento_total",
            "ticket_medio",
        ]

        company_summary[monetary_columns] = (
            company_summary[monetary_columns]
            .astype(float)
            .round(2)
        )

        company_summary[
            "participacao_historica"
        ] = (
            company_summary[
                "participacao_historica"
            ]
            .astype(float)
            .round(6)
        )

        integer_columns = [
            "pedidos_total",
            "dias_historico",
            "meses_com_movimento",
            "anos_com_movimento",
            "primeiro_ano",
            "ultimo_ano",
            "ranking_historico",
        ]

        for column in integer_columns:
            company_summary[column] = (
                pd.to_numeric(
                    company_summary[column],
                    errors="coerce",
                )
                .fillna(0)
                .astype(int)
            )

        ordered_columns = [
            "empresa",
            "nivel",
            "faturamento_total",
            "pedidos_total",
            "ticket_medio",
            "primeira_venda",
            "ultima_venda",
            "dias_historico",
            "meses_com_movimento",
            "anos_com_movimento",
            "primeiro_ano",
            "ultimo_ano",
            "participacao_historica",
            "ranking_historico",
        ]

        summary = pd.concat(
            [
                pd.DataFrame(
                    [consolidated]
                ),
                company_summary[
                    ordered_columns
                ],
            ],
            ignore_index=True,
            sort=False,
        )

        return summary[
            ordered_columns
        ].copy()

    def _prepare_dataframe(
        self,
        revenue_df: pd.DataFrame,
    ) -> pd.DataFrame:
        if revenue_df is None:
            raise ValueError(
                "A base de faturamento não pode ser None."
            )

        if revenue_df.empty:
            raise ValueError(
                "A base de faturamento está vazia."
            )

        missing_columns = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in revenue_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes: "
                + ", ".join(missing_columns)
            )

        revenue = revenue_df.copy()

        revenue["Data"] = pd.to_datetime(
            revenue["Data"],
            errors="coerce",
        )

        revenue["ano"] = pd.to_numeric(
            revenue["ano"],
            errors="coerce",
        )

        revenue["mes"] = pd.to_numeric(
            revenue["mes"],
            errors="coerce",
        )

        revenue["Valor_total_Unitario"] = (
            pd.to_numeric(
                revenue["Valor_total_Unitario"],
                errors="coerce",
            )
        )

        revenue = revenue[
            revenue["Data"].notna()
            & revenue["ano"].notna()
            & revenue["mes"].notna()
            & revenue[
                "Valor_total_Unitario"
            ].notna()
        ].copy()

        revenue["ano"] = (
            revenue["ano"]
            .astype(int)
        )

        revenue["mes"] = (
            revenue["mes"]
            .astype(int)
        )

        revenue["ano_mes"] = (
            revenue["Data"]
            .dt.to_period("M")
            .astype(str)
        )

        revenue["numero_pedido"] = (
            revenue["numero_pedido"]
            .fillna("SEM_PEDIDO")
            .astype(str)
            .str.strip()
        )

        revenue["Empresa"] = (
            revenue["Empresa"]
            .apply(
                CommercialDimensions.normalize_company
            )
        )

        revenue["Vendedor"] = (
            revenue["Vendedor"]
            .apply(
                CommercialDimensions.normalize_seller
            )
        )

        revenue["pedido_chave"] = (
            revenue["Empresa"]
            + "|"
            + revenue["numero_pedido"]
        )

        revenue["vendedor_chave"] = (
            revenue.apply(
                lambda row: (
                    CommercialDimensions.seller_identity(
                        company=row["Empresa"],
                        seller=row["Vendedor"],
                    )
                ),
                axis=1,
            )
        )

        return revenue

    def _build_month_calendar(
        self,
        revenue: pd.DataFrame,
    ) -> pd.DataFrame:
        available_years = sorted(
            revenue["ano"]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )

        records = []

        for year in available_years:
            for month in range(1, 13):
                records.append(
                    {
                        "ano": year,
                        "mes": month,
                        "ano_mes": (
                            f"{year}-{month:02d}"
                        ),
                    }
                )

        return pd.DataFrame(
            records
        )

    @staticmethod
    def _calculate_growth(
        current: pd.Series,
        previous: pd.Series,
    ) -> pd.Series:
        """
        Calcula crescimento percentual.

        Retorna NaN quando não existe base anterior
        ou quando a base anterior é zero.
        """
        return np.where(
            previous.notna()
            & (previous != 0),
            (
                (current - previous)
                / previous
            ),
            np.nan,
        )