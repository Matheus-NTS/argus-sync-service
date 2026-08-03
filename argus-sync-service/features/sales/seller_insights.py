from __future__ import annotations

import json

import pandas as pd


class SellerInsights:
    """
    Gera leituras executivas determinísticas por vendedor.

    O módulo utiliza apenas indicadores já calculados pelo backend:
    - posição e gaps da Arena;
    - atingimento atual e projeção;
    - ritmo atual e necessário;
    - Health Score e scorecards;
    - clientes, mix, ticket e faturamento.

    Nenhuma venda, meta ou projeção é recalculada aqui.
    """

    MAX_INSIGHTS = 5

    PRIORITY_ORDER = {
        "critical": 0,
        "warning": 1,
        "positive": 2,
        "neutral": 3,
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

        for index, row in result.iterrows():

            insights = self._build_insights(
                row=row,
                period_type=period_type,
            )

            ordered = sorted(
                insights,
                key=lambda item: (
                    self.PRIORITY_ORDER.get(
                        item["severity"],
                        99,
                    ),
                    item["priority"],
                ),
            )[: self.MAX_INSIGHTS]

            primary = (
                ordered[0]
                if ordered
                else self._fallback_insight()
            )

            result.at[
                index,
                "seller_insights",
            ] = json.dumps(
                ordered,
                ensure_ascii=False,
            )

            result.at[
                index,
                "seller_primary_insight",
            ] = primary["title"]

            result.at[
                index,
                "seller_primary_support",
            ] = primary["message"]

            result.at[
                index,
                "seller_primary_severity",
            ] = primary["severity"]

            result.at[
                index,
                "seller_recommended_action",
            ] = primary.get("action")

            result.at[
                index,
                "seller_insight_count",
            ] = len(ordered)

        result["seller_insight_count"] = (
            pd.to_numeric(
                result["seller_insight_count"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

        return result

    @staticmethod
    def _initialize_columns(
        dataframe: pd.DataFrame,
    ) -> None:

        dataframe["seller_insights"] = None
        dataframe["seller_primary_insight"] = (
            "Sem leitura disponível"
        )
        dataframe["seller_primary_support"] = (
            "Não há dados suficientes para gerar uma leitura."
        )
        dataframe["seller_primary_severity"] = (
            "neutral"
        )
        dataframe["seller_recommended_action"] = None
        dataframe["seller_insight_count"] = 0

    def _build_insights(
        self,
        row: pd.Series,
        period_type: str,
    ) -> list[dict]:

        insights: list[dict] = []

        self._append_arena_insight(
            insights,
            row,
        )

        self._append_projection_insight(
            insights,
            row,
            period_type,
        )

        self._append_pace_insight(
            insights,
            row,
        )

        self._append_health_insight(
            insights,
            row,
        )

        self._append_scorecard_insights(
            insights,
            row,
        )

        if not insights:
            insights.append(
                self._fallback_insight()
            )

        return insights

    def _append_arena_insight(
        self,
        insights: list[dict],
        row: pd.Series,
    ) -> None:

        position = self._optional_int(
            row.get("arena_position")
        )

        if position is None:
            return

        if position == 1:
            insights.append({
                "code": "arena_leader",
                "category": "arena",
                "severity": "positive",
                "priority": 10,
                "title": "Lidera a operação",
                "message": (
                    "Ocupa a primeira posição da Arena "
                    "no período selecionado."
                ),
                "action": (
                    "Preservar o ritmo e acompanhar "
                    "a sustentabilidade da liderança."
                ),
            })
            return

        gap_next = self._optional_float(
            row.get("arena_gap_next_pp")
        )

        if gap_next is None:
            return

        if gap_next <= 2:
            severity = "positive"
            title = "Próximo da posição acima"
            action = (
                "Priorizar oportunidades de curto prazo "
                "para avançar no ranking."
            )
        elif gap_next <= 5:
            severity = "neutral"
            title = "Disputa competitiva na Arena"
            action = (
                "Acompanhar o gap e buscar ganho gradual "
                "de atingimento."
            )
        else:
            severity = "warning"
            title = "Gap relevante na Arena"
            action = (
                "Revisar carteira e oportunidades para "
                "reduzir a distância da posição acima."
            )

        insights.append({
            "code": "arena_gap",
            "category": "arena",
            "severity": severity,
            "priority": 20,
            "title": title,
            "message": (
                f"Está a {gap_next:.2f} p.p. "
                "da posição imediatamente superior."
            ),
            "action": action,
        })

    def _append_projection_insight(
        self,
        insights: list[dict],
        row: pd.Series,
        period_type: str,
    ) -> None:

        if not bool(
            row.get("pace_applicable", False)
        ):
            return

        if not bool(
            row.get("meta_valida", False)
        ):
            insights.append({
                "code": "projection_without_target",
                "category": "projection",
                "severity": "neutral",
                "priority": 30,
                "title": "Sem meta válida",
                "message": (
                    "Não há meta válida para avaliar "
                    "a projeção do vendedor."
                ),
                "action": (
                    "Revisar o cadastro de meta antes "
                    "de interpretar a projeção."
                ),
            })
            return

        projected = self._optional_float(
            row.get("projecao_atingimento")
        )

        if projected is None:
            return

        if projected >= 1.37:
            title = "Projetado para hipermeta"
            severity = "positive"
            action = (
                "Preservar o ritmo e proteger "
                "as oportunidades em andamento."
            )
        elif projected >= 1.24:
            title = "Projetado para supermeta"
            severity = "positive"
            action = (
                "Manter o ritmo para consolidar "
                "a supermeta."
            )
        elif projected >= 1:
            title = "Projetado para atingir a meta"
            severity = "positive"
            action = (
                "Manter consistência até o fechamento "
                "do período."
            )
        elif projected >= 0.8:
            title = "Projeção próxima da meta"
            severity = "warning"
            action = (
                "Acelerar oportunidades com maior "
                "probabilidade de fechamento."
            )
        else:
            title = "Projeção abaixo da meta"
            severity = "critical"
            action = (
                "Revisar carteira, prioridades e ritmo "
                "necessário para recuperação."
            )

        insights.append({
            "code": "projection_status",
            "category": "projection",
            "severity": severity,
            "priority": 5,
            "title": title,
            "message": (
                "A projeção indica "
                f"{projected * 100:.1f}% "
                "de atingimento no fechamento."
            ),
            "action": action,
        })

    def _append_pace_insight(
        self,
        insights: list[dict],
        row: pd.Series,
    ) -> None:

        if not bool(
            row.get("pace_applicable", False)
        ):
            return

        current = self._optional_float(
            row.get("ritmo_atual")
        )
        required = self._optional_float(
            row.get("ritmo_necessario")
        )

        if current is None or required is None:
            return

        if required <= 0:
            insights.append({
                "code": "target_already_achieved",
                "category": "pace",
                "severity": "positive",
                "priority": 15,
                "title": "Meta já alcançada",
                "message": (
                    "Não há ritmo adicional necessário "
                    "para atingir a meta mensal."
                ),
                "action": (
                    "Direcionar o esforço para supermeta "
                    "e hipermeta."
                ),
            })
            return

        ratio = current / required

        if ratio >= 1.2:
            severity = "positive"
            title = "Ritmo acima do necessário"
            action = (
                "Manter a cadência e monitorar "
                "a qualidade das vendas."
            )
        elif ratio >= 1:
            severity = "positive"
            title = "Ritmo suficiente"
            action = (
                "Preservar o ritmo atual até "
                "o fechamento."
            )
        elif ratio >= 0.8:
            severity = "warning"
            title = "Ritmo exige atenção"
            action = (
                "Aumentar a cadência diária para "
                "evitar perda de projeção."
            )
        else:
            severity = "critical"
            title = "Ritmo insuficiente"
            action = (
                "Priorizar ações comerciais imediatas "
                "para recuperar o ritmo."
            )

        gap = max(
            required - current,
            0,
        )

        message = (
            f"Ritmo atual de R$ {current:,.2f} "
            f"ante R$ {required:,.2f} necessários."
        )

        if gap > 0:
            message += (
                f" Faltam R$ {gap:,.2f} por dia."
            )

        insights.append({
            "code": "pace_status",
            "category": "pace",
            "severity": severity,
            "priority": 8,
            "title": title,
            "message": message,
            "action": action,
        })

    def _append_health_insight(
        self,
        insights: list[dict],
        row: pd.Series,
    ) -> None:

        score = self._optional_float(
            row.get("seller_health_score")
        )

        status = str(
            row.get(
                "seller_health_status",
                "",
            )
            or ""
        )

        if score is None:
            return

        if status == "excellent":
            severity = "positive"
            title = "Operação comercial saudável"
            action = (
                "Preservar o equilíbrio entre "
                "performance, clientes, mix, ticket e ritmo."
            )
        elif status == "good":
            severity = "positive"
            title = "Boa saúde comercial"
            action = (
                "Atuar nos scorecards em atenção "
                "para elevar a consistência."
            )
        elif status == "attention":
            severity = "warning"
            title = "Saúde comercial em atenção"
            action = (
                "Revisar as dimensões com menor score "
                "e definir ações específicas."
            )
        else:
            severity = "critical"
            title = "Saúde comercial crítica"
            action = (
                "Priorizar plano de recuperação "
                "com acompanhamento próximo."
            )

        insights.append({
            "code": "health_status",
            "category": "health",
            "severity": severity,
            "priority": 12,
            "title": title,
            "message": (
                f"Health Score atual: {score:.1f} de 100."
            ),
            "action": action,
        })

    def _append_scorecard_insights(
        self,
        insights: list[dict],
        row: pd.Series,
    ) -> None:

        scorecards = self._parse_scorecards(
            row.get("seller_scorecards")
        )

        if not scorecards:
            return

        labels = {
            "clientes": "Clientes",
            "mix": "Mix",
            "ticket": "Ticket médio",
            "performance": "Performance",
            "ritmo": "Ritmo",
        }

        for key, card in scorecards.items():

            status = card.get("status")

            if status not in {
                "critical",
                "attention",
            }:
                continue

            severity = (
                "critical"
                if status == "critical"
                else "warning"
            )

            label = labels.get(
                key,
                key.capitalize(),
            )

            insights.append({
                "code": f"scorecard_{key}",
                "category": "scorecard",
                "severity": severity,
                "priority": (
                    25
                    if severity == "critical"
                    else 35
                ),
                "title": f"{label} exige atenção",
                "message": (
                    card.get("detail")
                    or (
                        f"O scorecard de {label.lower()} "
                        "está abaixo do desejado."
                    )
                ),
                "action": self._scorecard_action(
                    key
                ),
            })

    @staticmethod
    def _scorecard_action(
        key: str,
    ) -> str:

        actions = {
            "clientes": (
                "Ampliar a cobertura da carteira "
                "e estimular recorrência."
            ),
            "mix": (
                "Trabalhar venda cruzada e ampliar "
                "a variedade de produtos por cliente."
            ),
            "ticket": (
                "Revisar composição dos pedidos "
                "e oportunidades de maior valor."
            ),
            "performance": (
                "Priorizar oportunidades com maior "
                "impacto no atingimento da meta."
            ),
            "ritmo": (
                "Elevar a cadência diária de fechamento."
            ),
        }

        return actions.get(
            key,
            "Revisar a dimensão e definir ação específica.",
        )

    @staticmethod
    def _parse_scorecards(
        value,
    ) -> dict:

        if value is None:
            return {}

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}

            return (
                parsed
                if isinstance(parsed, dict)
                else {}
            )

        return {}

    @staticmethod
    def _fallback_insight() -> dict:

        return {
            "code": "no_specific_insight",
            "category": "general",
            "severity": "neutral",
            "priority": 99,
            "title": "Desempenho estável",
            "message": (
                "Não foram identificados desvios "
                "relevantes no período."
            ),
            "action": (
                "Manter acompanhamento regular."
            ),
        }

    @staticmethod
    def _optional_float(
        value,
    ) -> float | None:

        if value is None or pd.isna(value):
            return None

        return float(value)

    @staticmethod
    def _optional_int(
        value,
    ) -> int | None:

        if value is None or pd.isna(value):
            return None

        return int(value)