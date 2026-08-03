from __future__ import annotations

import pandas as pd


class SellerArena:
    """
    Constrói a classificação competitiva dos vendedores.

    Regras:
    - somente vendedores com arena_eligible=True participam;
    - ordenação por atingimento, faturamento, ticket médio e nome;
    - vendedores sem meta continuam no DataFrame, mas sem posição;
    - gaps são expressos em pontos percentuais;
    - o módulo não recalcula vendas, metas ou projeções.
    """

    APPLICABLE_PERIODS = {
        "current_month",
        "month_current",
        "month_previous",
        "ytd",
        "ytd_previous",
    }

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

        self._initialize_columns(result)

        if (
            result.empty
            or period_type not in self.APPLICABLE_PERIODS
        ):
            return result

        eligible_mask = (
            result.get(
                "arena_eligible",
                pd.Series(
                    False,
                    index=result.index,
                ),
            )
            .fillna(False)
            .astype(bool)
        )

        eligible = result[
            eligible_mask
        ].copy()

        if eligible.empty:
            return result

        eligible["atingimento"] = pd.to_numeric(
            eligible.get("atingimento"),
            errors="coerce",
        ).fillna(0.0)

        eligible["faturamento_total"] = pd.to_numeric(
            eligible.get("faturamento_total"),
            errors="coerce",
        ).fillna(0.0)

        eligible["ticket_medio"] = pd.to_numeric(
            eligible.get("ticket_medio"),
            errors="coerce",
        ).fillna(0.0)

        eligible["Vendedor"] = (
            eligible.get(
                "Vendedor",
                pd.Series(
                    "",
                    index=eligible.index,
                ),
            )
            .fillna("")
            .astype(str)
        )

        eligible = (
            eligible
            .sort_values(
                [
                    "atingimento",
                    "faturamento_total",
                    "ticket_medio",
                    "Vendedor",
                ],
                ascending=[
                    False,
                    False,
                    False,
                    True,
                ],
                kind="mergesort",
            )
            .reset_index()
            .rename(
                columns={
                    "index": "_original_index",
                }
            )
        )

        eligible["arena_position"] = (
            eligible.index + 1
        )

        leader_attainment = float(
            eligible.iloc[0]["atingimento"]
        )

        eligible["arena_gap_first_pp"] = (
            (
                leader_attainment
                - eligible["atingimento"]
            )
            * 100
        ).round(2)

        eligible["arena_gap_next_pp"] = 0.0

        for index in range(
            1,
            len(eligible),
        ):
            previous_attainment = float(
                eligible.iloc[
                    index - 1
                ]["atingimento"]
            )

            current_attainment = float(
                eligible.iloc[
                    index
                ]["atingimento"]
            )

            eligible.loc[
                index,
                "arena_gap_next_pp",
            ] = round(
                (
                    previous_attainment
                    - current_attainment
                )
                * 100,
                2,
            )

        eligible["arena_medal"] = (
            eligible["arena_position"]
            .apply(
                self._medal_for_position
            )
        )

        eligible["arena_level"] = (
            eligible.apply(
                self._classify_level,
                axis=1,
            )
        )

        eligible["arena_score"] = (
            eligible["atingimento"]
            .round(6)
        )

        eligible["arena_is_leader"] = (
            eligible["arena_position"] == 1
        )

        eligible["arena_highlight"] = (
            eligible.apply(
                self._build_highlight,
                axis=1,
            )
        )

        columns_to_merge = [
            "_original_index",
            "arena_position",
            "arena_score",
            "arena_medal",
            "arena_level",
            "arena_gap_first_pp",
            "arena_gap_next_pp",
            "arena_is_leader",
            "arena_highlight",
        ]

        arena_values = eligible[
            columns_to_merge
        ].set_index(
            "_original_index"
        )

        for column in columns_to_merge[1:]:
            result.loc[
                arena_values.index,
                column,
            ] = arena_values[column]

        result["arena_position"] = pd.to_numeric(
            result["arena_position"],
            errors="coerce",
        ).astype("Int64")

        return result

    @staticmethod
    def _initialize_columns(
        dataframe: pd.DataFrame,
    ) -> None:

        dataframe["arena_position"] = pd.NA
        dataframe["arena_score"] = pd.NA
        dataframe["arena_medal"] = None
        dataframe["arena_level"] = None
        dataframe["arena_gap_first_pp"] = pd.NA
        dataframe["arena_gap_next_pp"] = pd.NA
        dataframe["arena_is_leader"] = False
        dataframe["arena_highlight"] = None

    @staticmethod
    def _medal_for_position(
        position: int,
    ) -> str | None:

        medals = {
            1: "gold",
            2: "silver",
            3: "bronze",
        }

        return medals.get(
            int(position)
        )

    @staticmethod
    def _classify_level(
        row: pd.Series,
    ) -> str:

        status = str(
            row.get(
                "status_meta",
                "sem_meta",
            )
            or "sem_meta"
        )

        mapping = {
            "hipermeta": "elite",
            "supermeta": "ouro",
            "meta": "prata",
            "abaixo_meta": "bronze",
        }

        return mapping.get(
            status,
            "sem_classificacao",
        )

    @staticmethod
    def _build_highlight(
        row: pd.Series,
    ) -> str:

        if bool(
            row.get(
                "arena_is_leader",
                False,
            )
        ):
            return "Lidera a operação no período."

        projection_status = str(
            row.get(
                "status_projecao",
                "nao_aplicavel",
            )
            or "nao_aplicavel"
        )

        projection_attainment = row.get(
            "projecao_atingimento"
        )

        if (
            projection_status == "atinge_meta"
            and projection_attainment is not None
            and not pd.isna(
                projection_attainment
            )
        ):
            projection_value = float(
                projection_attainment
            )

            if projection_value >= 1.37:
                return (
                    "Projetado para atingir a hipermeta."
                )

            if projection_value >= 1.24:
                return (
                    "Projetado para atingir a supermeta."
                )

            return (
                "Projetado para atingir a meta."
            )

        required_pace = row.get(
            "ritmo_necessario"
        )

        current_pace = row.get(
            "ritmo_atual"
        )

        if (
            required_pace is not None
            and current_pace is not None
            and not pd.isna(required_pace)
            and not pd.isna(current_pace)
        ):
            pace_gap = max(
                float(required_pace)
                - float(current_pace),
                0.0,
            )

            if pace_gap > 0:
                return (
                    "Precisa elevar o ritmo diário em "
                    f"R$ {pace_gap:,.2f}."
                )

        gap_next = row.get(
            "arena_gap_next_pp"
        )

        if (
            gap_next is not None
            and not pd.isna(gap_next)
            and float(gap_next) > 0
        ):
            return (
                "Está a "
                f"{float(gap_next):.2f} p.p. "
                "da posição acima."
            )

        return (
            "Desempenho estável no período."
        )