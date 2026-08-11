from __future__ import annotations

import json

import pandas as pd


class SellerBenchmarks:
    """
    Publica comparações oficiais da equipe e o adversário imediatamente
    superior na Battle Arena.

    Regras:
    - usa somente indicadores já calculados no seller_df;
    - benchmark considera vendedores com faturamento no período;
    - comparação da Arena considera apenas arena_eligible=True;
    - não recalcula vendas, metas, projeções ou Health Score;
    - gap de faturamento para ultrapassar respeita o atingimento do
      adversário e a meta do próprio vendedor.
    """

    METRICS = (
        "faturamento_total",
        "pedidos",
        "clientes",
        "mix_produtos",
        "ticket_medio",
        "seller_health_score",
        "atingimento",
        "projecao_atingimento",
    )

    def build(
        self,
        seller_df: pd.DataFrame,
        period_type: str,
    ) -> pd.DataFrame:

        if seller_df is None:
            raise ValueError(
                "seller_df não pode ser None."
            )

        result = seller_df.copy()

        result["seller_team_benchmark"] = None
        result["seller_vs_team"] = None
        result["seller_next_opponent"] = None

        if result.empty:
            return result

        for metric in self.METRICS:
            if metric not in result.columns:
                result[metric] = pd.NA

            result[metric] = pd.to_numeric(
                result[metric],
                errors="coerce",
            )

        benchmark_mask = (
            result["faturamento_total"]
            .fillna(0)
            .gt(0)
        )

        benchmark_group = result[
            benchmark_mask
        ].copy()

        benchmark = self._build_benchmark(
            benchmark_group
        )

        eligible = result[
            result.get(
                "arena_eligible",
                pd.Series(
                    False,
                    index=result.index,
                ),
            )
            .fillna(False)
            .astype(bool)
            & result["arena_position"].notna()
        ].copy()

        eligible = eligible.sort_values(
            "arena_position",
            ascending=True,
        )

        opponent_by_key = (
            self._build_opponents(eligible)
        )

        for index, row in result.iterrows():
            seller_key = str(
                row.get("seller_key", "")
                or ""
            )

            result.at[
                index,
                "seller_team_benchmark",
            ] = json.dumps(
                benchmark,
                ensure_ascii=False,
            )

            result.at[
                index,
                "seller_vs_team",
            ] = json.dumps(
                self._compare_with_team(
                    row=row,
                    benchmark=benchmark,
                ),
                ensure_ascii=False,
            )

            opponent = opponent_by_key.get(
                seller_key
            )

            result.at[
                index,
                "seller_next_opponent",
            ] = (
                None
                if opponent is None
                else json.dumps(
                    opponent,
                    ensure_ascii=False,
                )
            )

        return result

    def _build_benchmark(
        self,
        dataframe: pd.DataFrame,
    ) -> dict:

        benchmark = {
            "seller_count": int(
                len(dataframe)
            ),
        }

        for metric in self.METRICS:
            values = pd.to_numeric(
                dataframe.get(metric),
                errors="coerce",
            ).dropna()

            benchmark[metric] = (
                None
                if values.empty
                else round(
                    float(values.mean()),
                    6,
                )
            )

        return benchmark

    def _compare_with_team(
        self,
        row: pd.Series,
        benchmark: dict,
    ) -> dict:

        comparison = {}

        for metric in self.METRICS:
            seller_value = self._optional_float(
                row.get(metric)
            )

            team_value = benchmark.get(metric)

            if (
                seller_value is None
                or team_value is None
            ):
                comparison[metric] = {
                    "value": seller_value,
                    "team_average": team_value,
                    "delta": None,
                    "delta_pct": None,
                }
                continue

            delta = seller_value - float(
                team_value
            )

            delta_pct = (
                delta / float(team_value)
                if float(team_value) != 0
                else None
            )

            comparison[metric] = {
                "value": round(
                    seller_value,
                    6,
                ),
                "team_average": round(
                    float(team_value),
                    6,
                ),
                "delta": round(
                    delta,
                    6,
                ),
                "delta_pct": (
                    None
                    if delta_pct is None
                    else round(
                        delta_pct,
                        6,
                    )
                ),
            }

        return comparison

    def _build_opponents(
        self,
        eligible: pd.DataFrame,
    ) -> dict[str, dict]:

        opponents = {}

        if eligible.empty:
            return opponents

        rows = list(
            eligible.to_dict(
                orient="records"
            )
        )

        for index, current in enumerate(rows):
            if index == 0:
                continue

            opponent = rows[index - 1]

            current_key = str(
                current.get("seller_key", "")
                or ""
            )

            if not current_key:
                continue

            own_meta = self._number(
                current.get("meta_mensal")
            )

            opponent_attainment = self._number(
                opponent.get("atingimento")
            )

            current_revenue = self._number(
                current.get(
                    "faturamento_total"
                )
            )

            required_revenue = (
                own_meta * opponent_attainment
                if own_meta > 0
                else current_revenue
            )

            opponents[current_key] = {
                "seller_key": opponent.get(
                    "seller_key"
                ),
                "vendedor": opponent.get(
                    "Vendedor"
                ),
                "arena_position": self._optional_int(
                    opponent.get(
                        "arena_position"
                    )
                ),
                "atingimento": round(
                    opponent_attainment,
                    6,
                ),
                "faturamento_total": round(
                    self._number(
                        opponent.get(
                            "faturamento_total"
                        )
                    ),
                    2,
                ),
                "pedidos": int(
                    self._number(
                        opponent.get("pedidos")
                    )
                ),
                "clientes": int(
                    self._number(
                        opponent.get("clientes")
                    )
                ),
                "mix_produtos": int(
                    self._number(
                        opponent.get(
                            "mix_produtos"
                        )
                    )
                ),
                "gap_atingimento_pp": round(
                    max(
                        opponent_attainment
                        - self._number(
                            current.get(
                                "atingimento"
                            )
                        ),
                        0,
                    )
                    * 100,
                    2,
                ),
                "gap_faturamento": round(
                    max(
                        required_revenue
                        - current_revenue,
                        0,
                    ),
                    2,
                ),
                "gap_pedidos": max(
                    int(
                        self._number(
                            opponent.get(
                                "pedidos"
                            )
                        )
                    )
                    - int(
                        self._number(
                            current.get(
                                "pedidos"
                            )
                        )
                    ),
                    0,
                ),
                "gap_clientes": max(
                    int(
                        self._number(
                            opponent.get(
                                "clientes"
                            )
                        )
                    )
                    - int(
                        self._number(
                            current.get(
                                "clientes"
                            )
                        )
                    ),
                    0,
                ),
                "gap_mix": max(
                    int(
                        self._number(
                            opponent.get(
                                "mix_produtos"
                            )
                        )
                    )
                    - int(
                        self._number(
                            current.get(
                                "mix_produtos"
                            )
                        )
                    ),
                    0,
                ),
            }

        return opponents

    @staticmethod
    def _number(value) -> float:

        if value is None or pd.isna(value):
            return 0.0

        return float(value)

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