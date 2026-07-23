import pandas as pd


class RevenueProjection:
    """
    Gera cenários anuais de projeção de faturamento.

    A projeção utiliza o faturamento realizado em cada mês
    do ano-base e aplica os percentuais de crescimento
    configurados.
    """

    DEFAULT_SCENARIOS = (
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,
    )

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

    def __init__(
        self,
        scenarios=None,
    ):
        self.scenarios = tuple(
            scenarios or self.DEFAULT_SCENARIOS
        )

    def build(
        self,
        revenue_df: pd.DataFrame,
        base_year: int,
    ) -> pd.DataFrame:
        self._validate_dataframe(revenue_df)

        base_year = int(base_year)
        projection_year = base_year + 1

        base_data = revenue_df[
            revenue_df["ano"] == base_year
        ].copy()

        if base_data.empty:
            raise ValueError(
                f"Não existem vendas para o ano-base {base_year}."
            )

        monthly_revenue = (
            base_data
            .groupby(
                "mes",
                as_index=False,
            )
            .agg(
                faturamento_base=(
                    "Valor_total_Unitario",
                    "sum",
                )
            )
        )

        month_dimension = pd.DataFrame({
            "mes": list(range(1, 13)),
        })

        projection = month_dimension.merge(
            monthly_revenue,
            on="mes",
            how="left",
        )

        projection["faturamento_base"] = (
            projection["faturamento_base"]
            .fillna(0)
            .astype(float)
        )

        projection["mes_nome"] = (
            projection["mes"]
            .map(self.MONTH_NAMES)
        )

        projection["ano_base"] = base_year
        projection["ano_projetado"] = projection_year

        annual_base_revenue = float(
            projection["faturamento_base"].sum()
        )

        if annual_base_revenue > 0:
            projection["participacao_ano_base"] = (
                projection["faturamento_base"]
                / annual_base_revenue
            )
        else:
            projection["participacao_ano_base"] = 0.0

        for scenario in self.scenarios:
            suffix = self._scenario_suffix(scenario)

            projection[
                f"projecao_{suffix}"
            ] = (
                projection["faturamento_base"]
                * (1 + scenario)
            )

            projection[
                f"crescimento_valor_{suffix}"
            ] = (
                projection[f"projecao_{suffix}"]
                - projection["faturamento_base"]
            )

        ordered_columns = [
            "ano_base",
            "ano_projetado",
            "mes",
            "mes_nome",
            "faturamento_base",
            "participacao_ano_base",
        ]

        for scenario in self.scenarios:
            suffix = self._scenario_suffix(scenario)

            ordered_columns.extend([
                f"projecao_{suffix}",
                f"crescimento_valor_{suffix}",
            ])

        projection = projection[
            ordered_columns
        ].copy()

        monetary_columns = [
            column
            for column in projection.columns
            if (
                column == "faturamento_base"
                or column.startswith("projecao_")
                or column.startswith("crescimento_valor_")
            )
        ]

        projection[monetary_columns] = (
            projection[monetary_columns]
            .round(2)
        )

        projection["participacao_ano_base"] = (
            projection["participacao_ano_base"]
            .round(6)
        )

        return projection

    def build_summary(
        self,
        projection_df: pd.DataFrame,
    ) -> pd.DataFrame:
        if projection_df is None or projection_df.empty:
            raise ValueError(
                "A projeção mensal está vazia."
            )

        annual_base_revenue = float(
            projection_df["faturamento_base"].sum()
        )

        records = []

        for scenario in self.scenarios:
            suffix = self._scenario_suffix(scenario)
            projection_column = f"projecao_{suffix}"

            projected_revenue = float(
                projection_df[projection_column].sum()
            )

            records.append({
                "ano_base": int(
                    projection_df["ano_base"].iloc[0]
                ),
                "ano_projetado": int(
                    projection_df["ano_projetado"].iloc[0]
                ),
                "cenario_percentual": scenario,
                "faturamento_ano_base": round(
                    annual_base_revenue,
                    2,
                ),
                "faturamento_projetado": round(
                    projected_revenue,
                    2,
                ),
                "crescimento_valor": round(
                    projected_revenue
                    - annual_base_revenue,
                    2,
                ),
                "media_mensal_projetada": round(
                    projected_revenue / 12,
                    2,
                ),
            })

        return pd.DataFrame(records)

    def build_long_format(
        self,
        projection_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Retorna uma linha por mês e cenário.

        Esse formato será o mais adequado para gravação
        futura no Supabase.
        """
        records = []

        for _, row in projection_df.iterrows():
            for scenario in self.scenarios:
                suffix = self._scenario_suffix(scenario)

                records.append({
                    "ano_base": int(row["ano_base"]),
                    "ano_projetado": int(
                        row["ano_projetado"]
                    ),
                    "mes": int(row["mes"]),
                    "mes_nome": row["mes_nome"],
                    "cenario_percentual": scenario,
                    "faturamento_base": round(
                        float(row["faturamento_base"]),
                        2,
                    ),
                    "participacao_ano_base": round(
                        float(
                            row["participacao_ano_base"]
                        ),
                        6,
                    ),
                    "faturamento_projetado": round(
                        float(row[f"projecao_{suffix}"]),
                        2,
                    ),
                    "crescimento_valor": round(
                        float(
                            row[
                                f"crescimento_valor_{suffix}"
                            ]
                        ),
                        2,
                    ),
                })

        return pd.DataFrame(records)

    @staticmethod
    def _scenario_suffix(
        scenario: float,
    ) -> str:
        percentage = int(round(scenario * 100))
        return f"{percentage}pct"

    @staticmethod
    def _validate_dataframe(
        revenue_df: pd.DataFrame,
    ) -> None:
        required_columns = [
            "ano",
            "mes",
            "Valor_total_Unitario",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in revenue_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes: "
                + ", ".join(missing_columns)
            )