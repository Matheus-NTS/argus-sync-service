from __future__ import annotations

from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd


class RevenueProjection:
    """
    Gera cenários de projeção de faturamento usando somente
    os meses encerrados do ano-base.

    Regras:
    - o ano-base é informado pela pipeline;
    - quando o ano-base é o ano corrente, somente meses
      anteriores ao mês da data de referência são encerrados;
    - meses ainda não encerrados permanecem nulos;
    - meses encerrados sem faturamento registrado são zero;
    - o ano projetado é sempre ano-base + 1;
    - os cenários são aplicados somente sobre a base encerrada.
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

    COMPANY_COLUMN_CANDIDATES = (
        "empresa",
        "Empresa",
    )

    REVENUE_COLUMN = "Valor_total_Unitario"

    def __init__(
        self,
        reference_date: date | None = None,
        scenarios: Iterable[float] | None = None,
    ):
        self.reference_date = reference_date or date.today()
        self.scenarios = tuple(
            scenarios or self.DEFAULT_SCENARIOS
        )

        if not self.scenarios:
            raise ValueError(
                "É necessário configurar ao menos um cenário."
            )

        invalid_scenarios = [
            scenario
            for scenario in self.scenarios
            if not isinstance(
                scenario,
                (int, float, np.integer, np.floating),
            )
            or not np.isfinite(float(scenario))
            or float(scenario) <= -1
        ]

        if invalid_scenarios:
            raise ValueError(
                "Cenários inválidos encontrados: "
                + ", ".join(
                    repr(value)
                    for value in invalid_scenarios
                )
            )

        self.scenarios = tuple(
            float(scenario)
            for scenario in self.scenarios
        )

    def build(
        self,
        revenue_df: pd.DataFrame,
        base_year: int,
    ) -> pd.DataFrame:
        """
        Constrói a projeção consolidada em formato largo.

        Meses encerrados sem movimento recebem faturamento
        igual a zero. O mês atual e os meses futuros ficam
        nulos quando o ano-base é o ano corrente.
        """
        self._validate_dataframe(revenue_df)

        base_year = int(base_year)
        projection_year = base_year + 1
        last_closed_month = self._last_closed_month(
            base_year
        )

        if last_closed_month < 1:
            raise ValueError(
                f"O ano-base {base_year} ainda não possui "
                "nenhum mês encerrado."
            )

        normalized = self._normalize_revenue_dataframe(
            revenue_df
        )

        base_data = normalized[
            normalized["ano"].eq(base_year)
        ].copy()

        if base_data.empty:
            raise ValueError(
                f"Não existem vendas para o ano-base "
                f"{base_year}."
            )

        monthly_revenue = (
            base_data[
                base_data["mes"].between(
                    1,
                    last_closed_month,
                )
            ]
            .groupby(
                "mes",
                as_index=False,
            )
            .agg(
                faturamento_base=(
                    self.REVENUE_COLUMN,
                    "sum",
                )
            )
        )

        projection = self._month_dimension(
            last_closed_month=last_closed_month
        ).merge(
            monthly_revenue,
            on="mes",
            how="left",
        )

        closed_mask = projection["mes_encerrado"]

        projection.loc[
            closed_mask,
            "faturamento_base",
        ] = (
            projection.loc[
                closed_mask,
                "faturamento_base",
            ]
            .fillna(0.0)
            .astype(float)
        )

        projection.loc[
            ~closed_mask,
            "faturamento_base",
        ] = np.nan

        projection["ano_base"] = base_year
        projection["ano_projetado"] = projection_year

        annual_base_revenue = float(
            projection.loc[
                closed_mask,
                "faturamento_base",
            ].sum()
        )

        projection["participacao_ano_base"] = np.nan

        if annual_base_revenue > 0:
            projection.loc[
                closed_mask,
                "participacao_ano_base",
            ] = (
                projection.loc[
                    closed_mask,
                    "faturamento_base",
                ]
                / annual_base_revenue
            )
        else:
            projection.loc[
                closed_mask,
                "participacao_ano_base",
            ] = 0.0

        for scenario in self.scenarios:
            suffix = self._scenario_suffix(scenario)
            projection_column = f"projecao_{suffix}"
            growth_column = (
                f"crescimento_valor_{suffix}"
            )

            projection[projection_column] = np.nan
            projection[growth_column] = np.nan

            projection.loc[
                closed_mask,
                projection_column,
            ] = (
                projection.loc[
                    closed_mask,
                    "faturamento_base",
                ]
                * (1 + scenario)
            )

            projection.loc[
                closed_mask,
                growth_column,
            ] = (
                projection.loc[
                    closed_mask,
                    projection_column,
                ]
                - projection.loc[
                    closed_mask,
                    "faturamento_base",
                ]
            )

        ordered_columns = [
            "ano_base",
            "ano_projetado",
            "mes",
            "mes_nome",
            "mes_encerrado",
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
                or column.startswith(
                    "crescimento_valor_"
                )
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

    def build_company_monthly(
        self,
        revenue_df: pd.DataFrame,
        base_year: int,
    ) -> pd.DataFrame:
        """
        Gera a projeção mensal por empresa.

        Todas as empresas com dados no ano-base são
        processadas com a mesma regra do consolidado.
        """
        self._validate_dataframe(revenue_df)

        company_column = self._resolve_company_column(
            revenue_df
        )

        if company_column is None:
            raise KeyError(
                "A base de faturamento não possui coluna "
                "de empresa."
            )

        normalized = revenue_df.copy()
        normalized[company_column] = (
            normalized[company_column]
            .astype("string")
            .str.strip()
        )

        companies = (
            normalized.loc[
                normalized[company_column].notna()
                & normalized[company_column].ne(""),
                company_column,
            ]
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

        frames: list[pd.DataFrame] = []

        for company in companies:
            company_revenue = normalized[
                normalized[company_column].eq(company)
            ].copy()

            try:
                company_projection = self.build(
                    revenue_df=company_revenue,
                    base_year=base_year,
                )
            except ValueError:
                continue

            company_projection["empresa"] = str(company)
            company_projection["nivel"] = "empresa"

            frames.append(
                self.build_long_format(
                    company_projection
                )
            )

        if not frames:
            return self._empty_company_monthly()

        return pd.concat(
            frames,
            ignore_index=True,
        )

    def build_company_summary(
        self,
        revenue_df: pd.DataFrame,
        base_year: int,
    ) -> pd.DataFrame:
        """
        Gera o resumo dos cenários por empresa.
        """
        self._validate_dataframe(revenue_df)

        company_column = self._resolve_company_column(
            revenue_df
        )

        if company_column is None:
            raise KeyError(
                "A base de faturamento não possui coluna "
                "de empresa."
            )

        normalized = revenue_df.copy()
        normalized[company_column] = (
            normalized[company_column]
            .astype("string")
            .str.strip()
        )

        companies = (
            normalized.loc[
                normalized[company_column].notna()
                & normalized[company_column].ne(""),
                company_column,
            ]
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

        frames: list[pd.DataFrame] = []

        for company in companies:
            company_revenue = normalized[
                normalized[company_column].eq(company)
            ].copy()

            try:
                company_projection = self.build(
                    revenue_df=company_revenue,
                    base_year=base_year,
                )
            except ValueError:
                continue

            company_projection["empresa"] = str(company)
            company_projection["nivel"] = "empresa"

            frames.append(
                self.build_summary(
                    company_projection
                )
            )

        if not frames:
            return self._empty_company_summary()

        return pd.concat(
            frames,
            ignore_index=True,
        )

    def build_summary(
        self,
        projection_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Resume cada cenário usando somente meses encerrados.

        A média mensal projetada usa a quantidade de meses
        encerrados, e não doze meses.
        """
        if projection_df is None or projection_df.empty:
            raise ValueError(
                "A projeção mensal está vazia."
            )

        self._validate_projection_dataframe(
            projection_df
        )

        closed_mask = self._closed_mask(
            projection_df
        )
        closed_months = int(closed_mask.sum())

        if closed_months < 1:
            raise ValueError(
                "A projeção não possui meses encerrados."
            )

        annual_base_revenue = float(
            projection_df.loc[
                closed_mask,
                "faturamento_base",
            ].sum()
        )

        records = []

        for scenario in self.scenarios:
            suffix = self._scenario_suffix(scenario)
            projection_column = f"projecao_{suffix}"

            if projection_column not in projection_df.columns:
                raise KeyError(
                    f"A coluna '{projection_column}' não "
                    "existe na projeção."
                )

            projected_revenue = float(
                projection_df.loc[
                    closed_mask,
                    projection_column,
                ].sum()
            )

            record = {
                "ano_base": int(
                    projection_df["ano_base"].iloc[0]
                ),
                "ano_projetado": int(
                    projection_df[
                        "ano_projetado"
                    ].iloc[0]
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
                    projected_revenue
                    / closed_months,
                    2,
                ),
            }

            if "empresa" in projection_df.columns:
                record["empresa"] = (
                    projection_df["empresa"].iloc[0]
                )
                record["nivel"] = (
                    projection_df.get(
                        "nivel",
                        pd.Series(["empresa"]),
                    ).iloc[0]
                )

            records.append(record)

        return pd.DataFrame(records)

    def build_long_format(
        self,
        projection_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Converte a projeção larga em uma linha por
        mês e cenário, preservando nulos nos meses não
        encerrados.
        """
        if projection_df is None or projection_df.empty:
            raise ValueError(
                "A projeção mensal está vazia."
            )

        self._validate_projection_dataframe(
            projection_df
        )

        records = []

        for _, row in projection_df.iterrows():
            for scenario in self.scenarios:
                suffix = self._scenario_suffix(scenario)

                record = {
                    "ano_base": int(row["ano_base"]),
                    "ano_projetado": int(
                        row["ano_projetado"]
                    ),
                    "mes": int(row["mes"]),
                    "mes_nome": row["mes_nome"],
                    "cenario_percentual": scenario,
                    "faturamento_base": (
                        self._round_nullable(
                            row["faturamento_base"],
                            2,
                        )
                    ),
                    "participacao_ano_base": (
                        self._round_nullable(
                            row[
                                "participacao_ano_base"
                            ],
                            6,
                        )
                    ),
                    "faturamento_projetado": (
                        self._round_nullable(
                            row[
                                f"projecao_{suffix}"
                            ],
                            2,
                        )
                    ),
                    "crescimento_valor": (
                        self._round_nullable(
                            row[
                                f"crescimento_valor_"
                                f"{suffix}"
                            ],
                            2,
                        )
                    ),
                }

                if "empresa" in projection_df.columns:
                    record["empresa"] = row["empresa"]
                    record["nivel"] = row.get(
                        "nivel",
                        "empresa",
                    )

                records.append(record)

        return pd.DataFrame(records)

    def _month_dimension(
        self,
        last_closed_month: int,
    ) -> pd.DataFrame:
        month_dimension = pd.DataFrame({
            "mes": list(range(1, 13)),
        })

        month_dimension["mes_nome"] = (
            month_dimension["mes"]
            .map(self.MONTH_NAMES)
        )

        month_dimension["mes_encerrado"] = (
            month_dimension["mes"]
            .le(last_closed_month)
        )

        return month_dimension

    def _last_closed_month(
        self,
        base_year: int,
    ) -> int:
        current_year = int(self.reference_date.year)

        if base_year < current_year:
            return 12

        if base_year > current_year:
            return 0

        return int(self.reference_date.month) - 1

    def _normalize_revenue_dataframe(
        self,
        revenue_df: pd.DataFrame,
    ) -> pd.DataFrame:
        normalized = revenue_df.copy()

        normalized["ano"] = pd.to_numeric(
            normalized["ano"],
            errors="coerce",
        )

        normalized["mes"] = pd.to_numeric(
            normalized["mes"],
            errors="coerce",
        )

        normalized[self.REVENUE_COLUMN] = (
            pd.to_numeric(
                normalized[self.REVENUE_COLUMN],
                errors="coerce",
            )
            .fillna(0.0)
        )

        normalized = normalized[
            normalized["ano"].notna()
            & normalized["mes"].notna()
        ].copy()

        normalized["ano"] = (
            normalized["ano"].astype(int)
        )

        normalized["mes"] = (
            normalized["mes"].astype(int)
        )

        normalized = normalized[
            normalized["mes"].between(1, 12)
        ].copy()

        return normalized

    @staticmethod
    def _closed_mask(
        projection_df: pd.DataFrame,
    ) -> pd.Series:
        if "mes_encerrado" in projection_df.columns:
            return (
                projection_df["mes_encerrado"]
                .fillna(False)
                .astype(bool)
            )

        return projection_df[
            "faturamento_base"
        ].notna()

    @classmethod
    def _resolve_company_column(
        cls,
        dataframe: pd.DataFrame,
    ) -> str | None:
        for column in cls.COMPANY_COLUMN_CANDIDATES:
            if column in dataframe.columns:
                return column

        return None

    @staticmethod
    def _scenario_suffix(
        scenario: float,
    ) -> str:
        percentage = int(round(scenario * 100))
        return f"{percentage}pct"

    @staticmethod
    def _round_nullable(
        value,
        decimals: int,
    ) -> float | None:
        if value is None:
            return None

        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            return None

        return round(float(value), decimals)

    @classmethod
    def _validate_dataframe(
        cls,
        revenue_df: pd.DataFrame,
    ) -> None:
        if revenue_df is None or revenue_df.empty:
            raise ValueError(
                "A base de faturamento está vazia."
            )

        required_columns = [
            "ano",
            "mes",
            cls.REVENUE_COLUMN,
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

    def _validate_projection_dataframe(
        self,
        projection_df: pd.DataFrame,
    ) -> None:
        required_columns = [
            "ano_base",
            "ano_projetado",
            "mes",
            "mes_nome",
            "faturamento_base",
            "participacao_ano_base",
        ]

        for scenario in self.scenarios:
            suffix = self._scenario_suffix(scenario)
            required_columns.extend([
                f"projecao_{suffix}",
                f"crescimento_valor_{suffix}",
            ])

        missing_columns = [
            column
            for column in required_columns
            if column not in projection_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes na "
                "projeção: "
                + ", ".join(missing_columns)
            )

    @staticmethod
    def _empty_company_monthly() -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "empresa",
            "nivel",
            "ano_base",
            "ano_projetado",
            "mes",
            "mes_nome",
            "cenario_percentual",
            "faturamento_base",
            "participacao_ano_base",
            "faturamento_projetado",
            "crescimento_valor",
        ])

    @staticmethod
    def _empty_company_summary() -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "empresa",
            "nivel",
            "ano_base",
            "ano_projetado",
            "cenario_percentual",
            "faturamento_ano_base",
            "faturamento_projetado",
            "crescimento_valor",
            "media_mensal_projetada",
        ])