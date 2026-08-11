from __future__ import annotations

import json

import pandas as pd


class SellerTimeline:
    """
    Deriva eventos executivos do histórico mensal consolidado.

    O módulo compara meses consecutivos do mesmo vendedor e não altera
    os indicadores oficiais publicados pelas demais features.
    """

    COLUMNS = [
        "event_date",
        "seller_key",
        "Vendedor",
        "event_type",
        "severity",
        "title",
        "description",
        "metadata",
    ]

    def build(
        self,
        monthly_df: pd.DataFrame,
        reference_date=None,
        include_current_month: bool = False,
    ) -> pd.DataFrame:

        if monthly_df is None or monthly_df.empty:
            return pd.DataFrame(
                columns=self.COLUMNS
            )

        required_columns = [
            "month_start",
            "seller_key",
            "Vendedor",
            "Empresa",
            "faturamento_total",
            "status_meta",
            "arena_position",
            "seller_health_score",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in monthly_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Não foi possível gerar SellerTimeline. "
                "Colunas ausentes: "
                + ", ".join(missing_columns)
            )

        base = monthly_df[
            monthly_df["Empresa"].eq("TOTAL")
        ].copy()

        if base.empty:
            return pd.DataFrame(
                columns=self.COLUMNS
            )

        base["month_start"] = pd.to_datetime(
            base["month_start"],
            errors="coerce",
        )

        base = base[
            base["month_start"].notna()
        ].copy()

        if not include_current_month:
            resolved_reference = pd.to_datetime(
                reference_date,
                errors="coerce",
            )

            if pd.isna(resolved_reference):
                resolved_reference = pd.Timestamp.today()

            current_month_start = (
                resolved_reference
                .to_period("M")
                .to_timestamp()
            )

            base = base[
                base["month_start"] < current_month_start
            ].copy()

        if base.empty:
            return pd.DataFrame(
                columns=self.COLUMNS
            )

        events = []

        for seller_key, group in base.groupby(
            "seller_key",
            sort=False,
        ):
            group = (
                group
                .sort_values("month_start")
                .reset_index(drop=True)
            )

            record_revenue = 0.0

            for index, row in group.iterrows():
                previous = (
                    group.iloc[index - 1]
                    if index > 0
                    else None
                )

                event_date = row[
                    "month_start"
                ].date().isoformat()

                revenue = self._number(
                    row.get("faturamento_total")
                )

                if (
                    revenue > record_revenue
                    and revenue > 0
                ):
                    events.append(
                        self._event(
                            event_date=event_date,
                            seller_key=seller_key,
                            vendedor=row["Vendedor"],
                            event_type="recorde_faturamento",
                            severity="positive",
                            title="Novo recorde mensal",
                            description=(
                                "Registrou o maior faturamento "
                                "mensal da série até então."
                            ),
                            metadata={
                                "faturamento_total": revenue,
                                "recorde_anterior": record_revenue,
                            },
                        )
                    )
                    record_revenue = revenue

                if previous is None:
                    continue

                self._append_arena_events(
                    events=events,
                    current=row,
                    previous=previous,
                    event_date=event_date,
                )

                self._append_goal_events(
                    events=events,
                    current=row,
                    previous=previous,
                    event_date=event_date,
                )

                self._append_health_events(
                    events=events,
                    current=row,
                    previous=previous,
                    event_date=event_date,
                )

        if not events:
            return pd.DataFrame(
                columns=self.COLUMNS
            )

        result = pd.DataFrame(events)

        result = (
            result
            .sort_values(
                [
                    "event_date",
                    "seller_key",
                    "event_type",
                ],
                ascending=[
                    False,
                    True,
                    True,
                ],
            )
            .reset_index(drop=True)
        )

        return result[
            self.COLUMNS
        ]

    def _append_arena_events(
        self,
        events: list[dict],
        current: pd.Series,
        previous: pd.Series,
        event_date: str,
    ) -> None:

        current_position = self._optional_int(
            current.get("arena_position")
        )

        previous_position = self._optional_int(
            previous.get("arena_position")
        )

        common = {
            "event_date": event_date,
            "seller_key": current["seller_key"],
            "vendedor": current["Vendedor"],
        }

        if (
            current_position is not None
            and previous_position is None
        ):
            events.append(
                self._event(
                    **common,
                    event_type="entrou_arena",
                    severity="positive",
                    title="Entrou na Battle Arena",
                    description=(
                        f"Passou a ocupar a "
                        f"{current_position}ª posição."
                    ),
                    metadata={
                        "position": current_position,
                    },
                )
            )
            return

        if (
            current_position is None
            and previous_position is not None
        ):
            events.append(
                self._event(
                    **common,
                    event_type="saiu_arena",
                    severity="warning",
                    title="Saiu da Battle Arena",
                    description=(
                        "Deixou de possuir posição "
                        "válida na Arena."
                    ),
                    metadata={
                        "previous_position": (
                            previous_position
                        ),
                    },
                )
            )
            return

        if (
            current_position is None
            or previous_position is None
            or current_position == previous_position
        ):
            return

        delta = (
            previous_position
            - current_position
        )

        if delta > 0:
            event_type = "subiu_posicao"
            severity = "positive"
            title = "Subiu no ranking"
            description = (
                f"Avançou {delta} posição"
                f"{'ões' if delta > 1 else ''} "
                "na Battle Arena."
            )
        else:
            drop = abs(delta)
            event_type = "caiu_posicao"
            severity = "warning"
            title = "Caiu no ranking"
            description = (
                f"Recuou {drop} posição"
                f"{'ões' if drop > 1 else ''} "
                "na Battle Arena."
            )

        events.append(
            self._event(
                **common,
                event_type=event_type,
                severity=severity,
                title=title,
                description=description,
                metadata={
                    "previous_position": previous_position,
                    "position": current_position,
                    "delta": delta,
                },
            )
        )

    def _append_goal_events(
        self,
        events: list[dict],
        current: pd.Series,
        previous: pd.Series,
        event_date: str,
    ) -> None:

        order = {
            "sem_meta": 0,
            "abaixo_meta": 1,
            "meta": 2,
            "supermeta": 3,
            "hipermeta": 4,
        }

        current_status = str(
            current.get(
                "status_meta",
                "sem_meta",
            )
        )

        previous_status = str(
            previous.get(
                "status_meta",
                "sem_meta",
            )
        )

        current_level = order.get(
            current_status,
            0,
        )

        previous_level = order.get(
            previous_status,
            0,
        )

        if current_level <= previous_level:
            return

        event_config = {
            "meta": (
                "atingiu_meta",
                "Meta alcançada",
            ),
            "supermeta": (
                "atingiu_supermeta",
                "Supermeta alcançada",
            ),
            "hipermeta": (
                "atingiu_hipermeta",
                "Hipermeta alcançada",
            ),
        }

        config = event_config.get(
            current_status
        )

        if config is None:
            return

        event_type, title = config

        events.append(
            self._event(
                event_date=event_date,
                seller_key=current["seller_key"],
                vendedor=current["Vendedor"],
                event_type=event_type,
                severity="positive",
                title=title,
                description=(
                    "Evoluiu de "
                    f"{previous_status} para "
                    f"{current_status}."
                ),
                metadata={
                    "previous_status": previous_status,
                    "status": current_status,
                },
            )
        )

    def _append_health_events(
        self,
        events: list[dict],
        current: pd.Series,
        previous: pd.Series,
        event_date: str,
    ) -> None:

        current_health = self._optional_float(
            current.get("seller_health_score")
        )

        previous_health = self._optional_float(
            previous.get("seller_health_score")
        )

        if (
            current_health is None
            or previous_health is None
        ):
            return

        delta = current_health - previous_health

        if abs(delta) < 10:
            return

        positive = delta > 0

        events.append(
            self._event(
                event_date=event_date,
                seller_key=current["seller_key"],
                vendedor=current["Vendedor"],
                event_type=(
                    "health_subiu"
                    if positive
                    else "health_caiu"
                ),
                severity=(
                    "positive"
                    if positive
                    else "warning"
                ),
                title=(
                    "Health Score avançou"
                    if positive
                    else "Health Score recuou"
                ),
                description=(
                    f"Variação de {delta:+.1f} pontos "
                    "em relação ao mês anterior."
                ),
                metadata={
                    "previous_health": previous_health,
                    "health": current_health,
                    "delta": delta,
                },
            )
        )

    @staticmethod
    def _event(
        event_date: str,
        seller_key: str,
        vendedor: str,
        event_type: str,
        severity: str,
        title: str,
        description: str,
        metadata: dict,
    ) -> dict:

        return {
            "event_date": event_date,
            "seller_key": seller_key,
            "Vendedor": vendedor,
            "event_type": event_type,
            "severity": severity,
            "title": title,
            "description": description,
            "metadata": json.dumps(
                metadata,
                ensure_ascii=False,
            ),
        }

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