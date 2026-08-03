from __future__ import annotations

import json

import numpy as np
import pandas as pd


class SellerScorecards:
    """
    Gera leituras executivas por vendedor sem recalcular vendas.

    Dimensões:
    - performance: meta atual e projeção;
    - clientes: amplitude e recorrência da carteira;
    - mix: variedade de produtos;
    - ticket: valor médio dos pedidos;
    - ritmo: ritmo atual versus ritmo necessário.

    Métricas comparativas usam percentis do próprio grupo do período.
    O Health Score não altera o ranking da Arena.
    """

    STATUS_CONFIG = {
        "excellent": {
            "label": "Excelente",
            "tone": "success",
            "icon": "award",
            "score": 100,
        },
        "good": {
            "label": "Bom",
            "tone": "positive",
            "icon": "trending-up",
            "score": 75,
        },
        "attention": {
            "label": "Atenção",
            "tone": "warning",
            "icon": "triangle-alert",
            "score": 50,
        },
        "critical": {
            "label": "Crítico",
            "tone": "danger",
            "icon": "circle-alert",
            "score": 25,
        },
        "not_applicable": {
            "label": "Não aplicável",
            "tone": "neutral",
            "icon": "minus",
            "score": None,
        },
    }

    HEALTH_WEIGHTS = {
        "performance": 0.35,
        "clientes": 0.20,
        "mix": 0.15,
        "ticket": 0.15,
        "ritmo": 0.15,
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

        if result.empty:
            return result

        numeric_columns = [
            "atingimento",
            "projecao_atingimento",
            "clientes",
            "pedidos",
            "mix_produtos",
            "ticket_medio",
            "ritmo_atual",
            "ritmo_necessario",
        ]

        for column in numeric_columns:
            if column not in result.columns:
                result[column] = np.nan

            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

        comparison_mask = (
            result["faturamento_total"]
            .fillna(0)
            .gt(0)
        )

        comparison = result[
            comparison_mask
        ].copy()

        clientes_thresholds = self._thresholds(
            comparison["clientes"]
        )
        recorrencia_thresholds = self._thresholds(
            self._safe_ratio(
                comparison["pedidos"],
                comparison["clientes"],
            )
        )
        mix_thresholds = self._thresholds(
            comparison["mix_produtos"]
        )
        ticket_thresholds = self._thresholds(
            comparison["ticket_medio"]
        )

        for index, row in result.iterrows():

            performance = self._performance_card(
                row
            )

            clientes = self._clients_card(
                row=row,
                clients_thresholds=clientes_thresholds,
                recurrence_thresholds=(
                    recorrencia_thresholds
                ),
            )

            mix = self._relative_card(
                value=row.get("mix_produtos"),
                thresholds=mix_thresholds,
                metric_label="Mix",
                detail_suffix=" produtos",
            )

            ticket = self._relative_card(
                value=row.get("ticket_medio"),
                thresholds=ticket_thresholds,
                metric_label="Ticket",
                currency=True,
            )

            ritmo = self._pace_card(
                row
            )

            cards = {
                "performance": performance,
                "clientes": clientes,
                "mix": mix,
                "ticket": ticket,
                "ritmo": ritmo,
            }

            health_score = self._health_score(
                cards
            )

            result.at[
                index,
                "seller_scorecards",
            ] = json.dumps(
                cards,
                ensure_ascii=False,
            )

            result.at[
                index,
                "seller_health_score",
            ] = health_score

            result.at[
                index,
                "seller_health_status",
            ] = self._health_status(
                health_score
            )

            result.at[
                index,
                "seller_health_label",
            ] = self.STATUS_CONFIG[
                result.at[
                    index,
                    "seller_health_status",
                ]
            ]["label"]

        result["seller_health_score"] = (
            pd.to_numeric(
                result["seller_health_score"],
                errors="coerce",
            )
            .fillna(0)
            .round(2)
        )

        return result

    @staticmethod
    def _initialize_columns(
        dataframe: pd.DataFrame,
    ) -> None:

        dataframe["seller_scorecards"] = None
        dataframe["seller_health_score"] = 0.0
        dataframe["seller_health_status"] = (
            "critical"
        )
        dataframe["seller_health_label"] = (
            "Crítico"
        )

    def _performance_card(
        self,
        row: pd.Series,
    ) -> dict:

        if not bool(
            row.get("meta_valida", False)
        ):
            return self._card(
                status="not_applicable",
                value=None,
                detail="Vendedor sem meta válida.",
            )

        actual = self._safe_float(
            row.get("atingimento")
        )

        projected = self._safe_float(
            row.get("projecao_atingimento")
        )

        reference = (
            projected
            if projected is not None
            else actual
        )

        if reference is None:
            status = "critical"
        elif reference >= 1.24:
            status = "excellent"
        elif reference >= 1.00:
            status = "good"
        elif reference >= 0.80:
            status = "attention"
        else:
            status = "critical"

        detail = (
            f"Realizado em {actual * 100:.1f}% da meta."
            if actual is not None
            else "Atingimento indisponível."
        )

        if projected is not None:
            detail += (
                f" Projeção de {projected * 100:.1f}%."
            )

        return self._card(
            status=status,
            value=actual,
            detail=detail,
        )

    def _clients_card(
        self,
        row: pd.Series,
        clients_thresholds: tuple[
            float,
            float,
            float,
        ] | None,
        recurrence_thresholds: tuple[
            float,
            float,
            float,
        ] | None,
    ) -> dict:

        clients = self._safe_float(
            row.get("clientes")
        )
        orders = self._safe_float(
            row.get("pedidos")
        )

        if clients is None or clients <= 0:
            return self._card(
                status="critical",
                value=0,
                detail="Sem clientes no período.",
            )

        recurrence = (
            orders / clients
            if orders is not None
            else 0
        )

        client_status = self._relative_status(
            clients,
            clients_thresholds,
        )

        recurrence_status = self._relative_status(
            recurrence,
            recurrence_thresholds,
        )

        status = self._average_status(
            [
                client_status,
                recurrence_status,
            ]
        )

        return self._card(
            status=status,
            value=clients,
            detail=(
                f"{int(clients)} clientes e "
                f"{recurrence:.2f} pedidos por cliente."
            ),
        )

    def _relative_card(
        self,
        value,
        thresholds: tuple[
            float,
            float,
            float,
        ] | None,
        metric_label: str,
        detail_suffix: str = "",
        currency: bool = False,
    ) -> dict:

        numeric = self._safe_float(value)

        if numeric is None:
            return self._card(
                status="not_applicable",
                value=None,
                detail=f"{metric_label} indisponível.",
            )

        status = self._relative_status(
            numeric,
            thresholds,
        )

        if currency:
            formatted = (
                f"R$ {numeric:,.2f}"
            )
        else:
            formatted = (
                f"{numeric:,.0f}{detail_suffix}"
            )

        return self._card(
            status=status,
            value=numeric,
            detail=(
                f"{metric_label} de {formatted} "
                "no período."
            ),
        )

    def _pace_card(
        self,
        row: pd.Series,
    ) -> dict:

        if not bool(
            row.get("pace_applicable", False)
        ):
            return self._card(
                status="not_applicable",
                value=None,
                detail=(
                    "Ritmo aplicável somente "
                    "ao mês corrente."
                ),
            )

        if not bool(
            row.get("meta_valida", False)
        ):
            return self._card(
                status="not_applicable",
                value=None,
                detail="Vendedor sem meta válida.",
            )

        current = self._safe_float(
            row.get("ritmo_atual")
        )
        required = self._safe_float(
            row.get("ritmo_necessario")
        )

        if current is None or required is None:
            return self._card(
                status="not_applicable",
                value=None,
                detail="Ritmo indisponível.",
            )

        if required <= 0:
            status = "excellent"
            ratio = None
            detail = "Meta já alcançada."
        else:
            ratio = current / required

            if ratio >= 1.20:
                status = "excellent"
            elif ratio >= 1.00:
                status = "good"
            elif ratio >= 0.80:
                status = "attention"
            else:
                status = "critical"

            gap = max(
                required - current,
                0,
            )

            detail = (
                f"Ritmo atual de R$ {current:,.2f}; "
                f"necessário de R$ {required:,.2f}."
            )

            if gap > 0:
                detail += (
                    f" Gap diário de R$ {gap:,.2f}."
                )

        return self._card(
            status=status,
            value=ratio,
            detail=detail,
        )

    def _card(
        self,
        status: str,
        value,
        detail: str,
    ) -> dict:

        config = self.STATUS_CONFIG[status]

        return {
            "status": status,
            "label": config["label"],
            "tone": config["tone"],
            "icon": config["icon"],
            "score": config["score"],
            "value": (
                None
                if value is None
                else round(float(value), 6)
            ),
            "detail": detail,
        }

    def _health_score(
        self,
        cards: dict,
    ) -> float:

        weighted_total = 0.0
        applied_weight = 0.0

        for key, weight in (
            self.HEALTH_WEIGHTS.items()
        ):
            score = cards[key].get("score")

            if score is None:
                continue

            weighted_total += (
                float(score) * weight
            )
            applied_weight += weight

        if applied_weight <= 0:
            return 0.0

        return round(
            weighted_total / applied_weight,
            2,
        )

    @staticmethod
    def _health_status(
        score: float,
    ) -> str:

        if score >= 85:
            return "excellent"

        if score >= 70:
            return "good"

        if score >= 50:
            return "attention"

        return "critical"

    @classmethod
    def _relative_status(
        cls,
        value: float,
        thresholds: tuple[
            float,
            float,
            float,
        ] | None,
    ) -> str:

        if thresholds is None:
            return "attention"

        q30, q60, q80 = thresholds

        if value >= q80:
            return "excellent"

        if value >= q60:
            return "good"

        if value >= q30:
            return "attention"

        return "critical"

    def _average_status(
        self,
        statuses: list[str],
    ) -> str:

        scores = [
            self.STATUS_CONFIG[status]["score"]
            for status in statuses
            if self.STATUS_CONFIG[status][
                "score"
            ] is not None
        ]

        if not scores:
            return "not_applicable"

        average = sum(scores) / len(scores)

        return self._health_status(
            average
        )

    @staticmethod
    def _thresholds(
        series: pd.Series,
    ) -> tuple[
        float,
        float,
        float,
    ] | None:

        values = pd.to_numeric(
            series,
            errors="coerce",
        ).dropna()

        if values.empty:
            return None

        return (
            float(values.quantile(0.30)),
            float(values.quantile(0.60)),
            float(values.quantile(0.80)),
        )

    @staticmethod
    def _safe_ratio(
        numerator: pd.Series,
        denominator: pd.Series,
    ) -> pd.Series:

        safe_denominator = (
            pd.to_numeric(
                denominator,
                errors="coerce",
            )
            .replace(0, np.nan)
        )

        return (
            pd.to_numeric(
                numerator,
                errors="coerce",
            )
            / safe_denominator
        )

    @staticmethod
    def _safe_float(
        value,
    ) -> float | None:

        if value is None or pd.isna(value):
            return None

        return float(value)