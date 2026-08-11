from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
from typing import Any


SEVERITY_RANK = {
    "healthy": 0,
    "monitoring": 1,
    "attention": 2,
    "critical": 3,
}

PRIORITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

ATTENTION_QUOTAS = {
    "stock": 3,
    "customers": 2,
    "products": 2,
    "profitability": 2,
    "commercial": 1,
    "lost_sales": 1,
}


def num(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def text(value: Any, default: str = "") -> str:
    return str(value).strip() if value is not None else default


def severity(value: Any) -> str:
    current = text(value, "monitoring").lower()
    aliases = {
        "success": "healthy",
        "info": "monitoring",
        "warning": "attention",
        "medium": "attention",
        "high": "critical",
    }
    current = aliases.get(current, current)
    return current if current in SEVERITY_RANK else "monitoring"


def priority(value: Any) -> str:
    current = text(value, "medium").lower()
    aliases = {
        "urgent": "critical",
        "alta": "high",
        "média": "medium",
        "media": "medium",
        "baixa": "low",
    }
    current = aliases.get(current, current)
    return current if current in PRIORITY_RANK else "medium"


def stable_key(*parts: Any) -> str:
    payload = "|".join(text(part).lower() for part in parts)
    return sha1(payload.encode("utf-8")).hexdigest()


def brl(value: float) -> str:
    formatted = (
        f"{value:,.2f}"
        .replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )
    return f"R$ {formatted}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def pt_decimal(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


RISK_LABELS = {
    "high_value_low_frequency": "alto valor com baixa recorrência",
    "low_customer_base": "base de clientes restrita",
    "low_product_mix": "baixa diversidade de produtos por cliente",
    "customer_low_profitability": "rentabilidade abaixo do esperado por cliente",
    "product_low_profitability": "rentabilidade abaixo do esperado por produto",
    "product_loss": "produtos com prejuízo",
    "customer_loss": "clientes com prejuízo",
    "negative_margin": "margem negativa",
    "low_margin": "margem baixa",
    "ruptura": "ruptura",
    "excesso": "excesso de estoque",
    "sem_giro": "estoque sem giro",
    "customer_risk": "risco na carteira de clientes",
    "product_risk": "risco no portfólio de produtos",
    "profitability_risk": "risco de rentabilidade",
}


def risk_label(value: Any) -> str:
    key = text(value).lower()
    return RISK_LABELS.get(
        key,
        key.replace("_", " ").strip() or "sinal de atenção",
    )


def customer_attention_title(risk_type: str, count: int) -> str:
    labels = {
        "high_value_low_frequency": (
            f"{count} clientes relevantes compram com baixa frequência"
        ),
        "low_customer_base": (
            f"{count} clientes indicam concentração excessiva da base"
        ),
        "low_product_mix": (
            f"{count} clientes compram uma variedade limitada de produtos"
        ),
        "customer_low_profitability": (
            f"{count} clientes apresentam rentabilidade abaixo do esperado"
        ),
        "customer_loss": (
            f"{count} clientes geram prejuízo no período"
        ),
    }
    return labels.get(
        risk_type,
        f"{count} clientes apresentam {risk_label(risk_type)}",
    )


def product_attention_title(risk_type: str, count: int) -> str:
    labels = {
        "low_product_mix": (
            f"{count} produtos revelam baixa diversificação do mix"
        ),
        "product_low_profitability": (
            f"{count} produtos apresentam rentabilidade abaixo do esperado"
        ),
        "product_loss": (
            f"{count} produtos geram prejuízo no período"
        ),
        "negative_margin": (
            f"{count} produtos operam com margem negativa"
        ),
        "low_margin": (
            f"{count} produtos operam com margem baixa"
        ),
    }
    return labels.get(
        risk_type,
        f"{count} produtos apresentam {risk_label(risk_type)}",
    )


def profitability_attention_title(risk_type: str, count: int) -> str:
    labels = {
        "product_loss": (
            f"{count} produtos pressionam o lucro com resultado negativo"
        ),
        "customer_loss": (
            f"{count} clientes pressionam o lucro com resultado negativo"
        ),
        "negative_margin": (
            f"{count} dimensões operam com margem negativa"
        ),
        "low_margin": (
            f"{count} dimensões operam com margem abaixo do esperado"
        ),
        "customer_low_profitability": (
            f"{count} clientes apresentam rentabilidade abaixo do esperado"
        ),
        "product_low_profitability": (
            f"{count} produtos apresentam rentabilidade abaixo do esperado"
        ),
    }
    return labels.get(
        risk_type,
        f"{count} dimensões apresentam {risk_label(risk_type)}",
    )


def abc_weight(value: Any) -> float:
    curve = text(value).upper()
    return {
        "A": 5.0,
        "B": 3.0,
        "C": 2.0,
        "D": 1.0,
        "E": 0.5,
    }.get(curve, 0.0)


def stock_impact(row: dict[str, Any]) -> float:
    """
    Ruptura não pode ser ordenada por valor_estoque, pois ele tende a zero.
    Usa impacto comercial recente + volume + curva ABC.
    """
    revenue_90d = num(row.get("faturamento_90d"))
    qty_90d = num(row.get("qtd_vendida_90d"))
    curve = abc_weight(row.get("curva_abcde"))
    return revenue_90d + (qty_90d * 100.0) + (curve * 1000.0)


class ArgusAiEngine:
    """Transforma marts existentes em inteligência executiva determinística."""

    def build(
        self,
        reference_date: str,
        period_type: str,
        executive_snapshot: dict[str, Any],
        previous_snapshot: dict[str, Any] | None,
        commercial: dict[str, Any] | None,
        stock: dict[str, Any] | None,
        customers: dict[str, Any] | None,
        products: dict[str, Any] | None,
        profitability: dict[str, Any] | None,
        sellers: list[dict[str, Any]],
        commercial_alerts: list[dict[str, Any]],
        commercial_recommendations: list[dict[str, Any]],
        customer_risks: list[dict[str, Any]],
        product_risks: list[dict[str, Any]],
        stock_risks: list[dict[str, Any]],
        profitability_risks: list[dict[str, Any]],
        profitability_recommendations: list[dict[str, Any]],
        lost_sales: list[dict[str, Any]],
    ) -> dict[str, Any]:
        changes = self._changes(
            reference_date,
            period_type,
            executive_snapshot,
            previous_snapshot,
            sellers,
        )

        attention = self._attention(
            reference_date,
            period_type,
            commercial_alerts,
            customer_risks,
            product_risks,
            stock_risks,
            profitability_risks,
            lost_sales,
        )

        opportunities = self._opportunities(
            reference_date,
            period_type,
            commercial,
            stock,
            customers,
            products,
            profitability,
            sellers,
            commercial_recommendations,
            profitability_recommendations,
        )

        actions = self._actions(
            reference_date,
            period_type,
            attention,
            opportunities,
        )

        briefing = self._briefing(
            reference_date,
            period_type,
            executive_snapshot,
            commercial,
            stock,
            customers,
            products,
            profitability,
            changes,
            attention,
            opportunities,
            actions,
        )

        events = self._events(
            reference_date,
            period_type,
            changes,
            attention,
            opportunities,
        )

        return {
            "briefing": briefing,
            "changes": changes,
            "attention": attention,
            "opportunities": opportunities,
            "actions": actions,
            "events": events,
        }

    def _changes(self, ref, period, current, previous, sellers):
        items = []

        if previous:
            metrics = [
                ("faturamento_total", "Faturamento"),
                ("ticket_medio", "Ticket médio"),
                ("clientes", "Clientes compradores"),
                ("pedidos", "Pedidos"),
            ]

            for order, (key, label) in enumerate(metrics, 1):
                now = num(current.get(key))
                before = num(previous.get(key))

                if before == 0:
                    continue

                variation = now - before
                variation_pct = variation / abs(before)

                if abs(variation_pct) < 0.03:
                    continue

                items.append({
                    "reference_date": ref,
                    "period_type": period,
                    "item_key": stable_key("change", key, ref),
                    "source_module": "commercial",
                    "change_type": key,
                    "direction": "up" if variation > 0 else "down",
                    "severity": "healthy" if variation > 0 else "attention",
                    "title": (
                        f"{label} "
                        f"{'avançou' if variation > 0 else 'recuou'}"
                    ),
                    "description": (
                        f"{label} variou {pct(abs(variation_pct))} "
                        "frente ao snapshot anterior."
                    ),
                    "previous_value": round(before, 4),
                    "current_value": round(now, 4),
                    "variation_value": round(variation, 4),
                    "variation_percent": round(variation_pct, 6),
                    "sort_order": order,
                })

        eligible = [
            row
            for row in sellers
            if row.get("arena_eligible")
            and row.get("arena_position") is not None
        ]

        eligible.sort(
            key=lambda row: (
                integer(row.get("arena_position")) or 999999,
                -num(row.get("atingimento")),
                -num(row.get("faturamento_total")),
            )
        )

        if eligible:
            leader = eligible[0]
            items.append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "leader",
                    leader.get("seller_key"),
                    ref,
                ),
                "source_module": "commercial",
                "change_type": "seller_leadership",
                "direction": "leader",
                "severity": "healthy",
                "title": "Liderança comercial do período",
                "description": (
                    f"{text(leader.get('vendedor'), 'Vendedor')} lidera "
                    f"a arena com {pct(num(leader.get('atingimento')))} "
                    "de atingimento."
                ),
                "previous_value": None,
                "current_value": round(
                    num(leader.get("atingimento")),
                    6,
                ),
                "variation_value": None,
                "variation_percent": None,
                "sort_order": 20,
            })

        return items[:8]

    def _attention(
        self,
        ref,
        period,
        alerts,
        customer_risks,
        product_risks,
        stock_risks,
        profit_risks,
        lost_sales,
    ):
        """
        Gera uma leitura executiva macro primeiro.

        A tela da IA ARGUS não deve funcionar como listagem operacional.
        Cada frente produz sinais consolidados e, quando útil, no máximo
        um exemplo individual de maior impacto.
        """
        pools: dict[str, list[dict[str, Any]]] = defaultdict(list)

        def add(
            source,
            kind,
            sev,
            prio,
            title,
            description,
            action,
            entity_type=None,
            entity_key=None,
            empresa=None,
            evidence_text=None,
            evidence_value=None,
            impact_score=0.0,
        ):
            pools[source].append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "attention",
                    source,
                    kind,
                    entity_key or title,
                    ref,
                ),
                "source_module": source,
                "attention_type": kind,
                "severity": severity(sev),
                "priority": priority(prio),
                "title": title,
                "description": description,
                "recommended_action": action,
                "entity_type": entity_type,
                "entity_key": entity_key,
                "empresa": empresa,
                "evidence_text": evidence_text,
                "evidence_value": evidence_value,
                "sort_order": 0,
                "_impact_score": impact_score,
            })

        for row in alerts:
            alert_title = text(
                row.get("title"),
                "Alerta comercial",
            )
            alert_description = text(
                row.get("description"),
            )
            alert_severity = severity(
                row.get("severity")
            )
            neutral_text = (
                f"{alert_title} {alert_description}"
                .lower()
            )

            is_neutral_message = any(
                marker in neutral_text
                for marker in (
                    "nenhum alerta",
                    "sem alerta",
                    "não há alerta",
                    "nao ha alerta",
                    "nenhum sinal crítico",
                    "nenhum sinal critico",
                )
            )

            if (
                alert_severity in {"healthy", "monitoring"}
                and is_neutral_message
            ):
                continue

            add(
                "commercial",
                text(row.get("alert_type"), "alert"),
                alert_severity,
                "high",
                alert_title,
                alert_description,
                "Revisar o sinal no módulo Comercial e definir responsável.",
            )

        self._add_customer_attention(
            pools=pools,
            ref=ref,
            period=period,
            customer_risks=customer_risks,
        )

        self._add_product_attention(
            pools=pools,
            ref=ref,
            period=period,
            product_risks=product_risks,
        )

        self._add_balanced_stock_attention(
            pools=pools,
            ref=ref,
            period=period,
            stock_risks=stock_risks,
        )

        self._add_profitability_attention(
            pools=pools,
            ref=ref,
            period=period,
            profit_risks=profit_risks,
        )

        valid_lost = [
            row
            for row in lost_sales
            if text(
                row.get("data_quality_status"),
                "valid",
            ) != "invalid"
        ]

        lost_value = sum(
            num(row.get("valor_total"))
            for row in valid_lost
        )

        if lost_value > 0:
            add(
                "lost_sales",
                "lost_sales_value",
                "attention",
                "high",
                "Vendas perdidas exigem recuperação",
                (
                    f"A base registra {len(valid_lost)} ocorrências analisáveis, "
                    f"somando {brl(lost_value)} em vendas perdidas."
                ),
                (
                    "Atacar os motivos recorrentes e separar as oportunidades "
                    "com maior chance de recuperação."
                ),
                "metric",
                "lost_sales_value",
                evidence_text=(
                    f"{len(valid_lost)} registros · {brl(lost_value)}"
                ),
                evidence_value=lost_value,
                impact_score=lost_value,
            )

        # Unicidade dentro de cada frente antes das cotas.
        for source, rows in list(pools.items()):
            deduplicated: dict[str, dict[str, Any]] = {}

            for row in rows:
                key = row["item_key"]
                existing = deduplicated.get(key)

                if existing is None:
                    deduplicated[key] = row
                    continue

                current_rank = (
                    PRIORITY_RANK[row["priority"]],
                    SEVERITY_RANK[row["severity"]],
                    abs(num(row.get("_impact_score"))),
                )
                existing_rank = (
                    PRIORITY_RANK[existing["priority"]],
                    SEVERITY_RANK[existing["severity"]],
                    abs(num(existing.get("_impact_score"))),
                )

                if current_rank > existing_rank:
                    deduplicated[key] = row

            pools[source] = list(deduplicated.values())

        for rows in pools.values():
            rows.sort(
                key=lambda row: (
                    -PRIORITY_RANK[row["priority"]],
                    -SEVERITY_RANK[row["severity"]],
                    -abs(num(row.get("_impact_score"))),
                    row["title"],
                )
            )

        selected: list[dict[str, Any]] = []
        leftovers: list[dict[str, Any]] = []

        for source in [
            "stock",
            "customers",
            "products",
            "profitability",
            "commercial",
            "lost_sales",
        ]:
            rows = pools.get(source, [])
            quota = ATTENTION_QUOTAS.get(source, 0)
            selected.extend(rows[:quota])
            leftovers.extend(rows[quota:])

        selected_keys = {row["item_key"] for row in selected}
        selected_count_by_source = defaultdict(int)

        for row in selected:
            selected_count_by_source[
                row["source_module"]
            ] += 1

        leftovers = [
            row
            for row in leftovers
            if row["item_key"] not in selected_keys
        ]
        leftovers.sort(
            key=lambda row: (
                -PRIORITY_RANK[row["priority"]],
                -SEVERITY_RANK[row["severity"]],
                -abs(num(row.get("_impact_score"))),
                row["title"],
            )
        )

        for row in leftovers:
            if len(selected) >= 12:
                break

            source = row["source_module"]
            source_cap = ATTENTION_QUOTAS.get(
                source,
                0,
            )

            if selected_count_by_source[source] >= source_cap:
                continue

            selected.append(row)
            selected_count_by_source[source] += 1

        unique_selected: dict[str, dict[str, Any]] = {}

        for row in selected:
            key = row["item_key"]
            existing = unique_selected.get(key)

            if existing is None:
                unique_selected[key] = row
                continue

            current_rank = (
                PRIORITY_RANK[row["priority"]],
                SEVERITY_RANK[row["severity"]],
                abs(num(row.get("_impact_score"))),
            )
            existing_rank = (
                PRIORITY_RANK[existing["priority"]],
                SEVERITY_RANK[existing["severity"]],
                abs(num(existing.get("_impact_score"))),
            )

            if current_rank > existing_rank:
                unique_selected[key] = row

        selected = list(unique_selected.values())
        selected.sort(
            key=lambda row: (
                -PRIORITY_RANK[row["priority"]],
                -SEVERITY_RANK[row["severity"]],
                -abs(num(row.get("_impact_score"))),
                row["source_module"],
                row["title"],
            )
        )
        selected = selected[:12]

        for index, row in enumerate(selected, 1):
            row["sort_order"] = index
            row.pop("_impact_score", None)

        return selected

    def _add_customer_attention(
        self,
        *,
        pools,
        ref,
        period,
        customer_risks,
    ):
        if not customer_risks:
            return

        grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

        for row in customer_risks:
            risk_type = text(
                row.get("risk_type"),
                "customer_risk",
            )
            customer_key = (
                text(row.get("codigo_cliente"))
                or stable_key(
                    text(row.get("cliente")),
                    text(row.get("empresa")),
                )
            )

            existing = grouped[risk_type].get(
                customer_key
            )

            if existing is None:
                grouped[risk_type][customer_key] = row
                continue

            current_rank = SEVERITY_RANK[
                severity(row.get("severity"))
            ]
            existing_rank = SEVERITY_RANK[
                severity(existing.get("severity"))
            ]

            if current_rank > existing_rank:
                grouped[risk_type][customer_key] = row

        aggregates = []

        for risk_type, unique_map in grouped.items():
            rows = list(unique_map.values())
            unique_count = len(rows)

            examples = [
                text(
                    row.get("cliente"),
                    "Cliente não identificado",
                )
                for row in rows[:3]
            ]

            critical_count = sum(
                1
                for row in rows
                if severity(row.get("severity")) == "critical"
            )

            aggregate_severity = (
                "critical"
                if critical_count > 0
                else "attention"
            )

            label = risk_label(risk_type)

            aggregates.append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "attention",
                    "customers",
                    "aggregate",
                    risk_type,
                    ref,
                ),
                "source_module": "customers",
                "attention_type": f"{risk_type}_aggregate",
                "severity": aggregate_severity,
                "priority": "high",
                "title": customer_attention_title(
                    risk_type,
                    unique_count,
                ),
                "description": (
                    f"A análise identificou {unique_count} clientes únicos "
                    f"com {label}. Entre os casos de referência estão "
                    f"{', '.join(examples)}."
                ),
                "recommended_action": (
                    "Segmentar a carteira por valor e recência, definir responsável "
                    "e acompanhar a recuperação dos casos prioritários."
                ),
                "entity_type": "customer_portfolio",
                "entity_key": risk_type,
                "empresa": None,
                "evidence_text": (
                    f"{unique_count} clientes únicos · "
                    f"{critical_count} críticos"
                ),
                "evidence_value": float(unique_count),
                "sort_order": 0,
                "_impact_score": (
                    unique_count * 1000
                    + critical_count * 5000
                ),
            })

        aggregates.sort(
            key=lambda row: (
                -SEVERITY_RANK[row["severity"]],
                -row["_impact_score"],
                row["title"],
            )
        )

        pools["customers"].extend(
            aggregates[:2]
        )

    def _add_product_attention(
        self,
        *,
        pools,
        ref,
        period,
        product_risks,
    ):
        if not product_risks:
            return

        grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

        for row in product_risks:
            risk_type = text(
                row.get("risk_type"),
                "product_risk",
            )
            product_key = (
                text(row.get("prod_codigo"))
                or stable_key(
                    text(row.get("produto")),
                    text(row.get("empresa")),
                )
            )

            existing = grouped[risk_type].get(
                product_key
            )

            if existing is None:
                grouped[risk_type][product_key] = row
                continue

            current_rank = SEVERITY_RANK[
                severity(row.get("severity"))
            ]
            existing_rank = SEVERITY_RANK[
                severity(existing.get("severity"))
            ]

            if current_rank > existing_rank:
                grouped[risk_type][product_key] = row

        aggregates = []

        for risk_type, unique_map in grouped.items():
            rows = list(unique_map.values())
            unique_count = len(rows)

            examples = [
                text(
                    row.get("produto"),
                    "Produto não identificado",
                )
                for row in rows[:3]
            ]

            critical_count = sum(
                1
                for row in rows
                if severity(row.get("severity")) == "critical"
            )

            aggregate_severity = (
                "critical"
                if critical_count > 0
                else "attention"
            )

            label = risk_label(risk_type)

            aggregates.append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "attention",
                    "products",
                    "aggregate",
                    risk_type,
                    ref,
                ),
                "source_module": "products",
                "attention_type": f"{risk_type}_aggregate",
                "severity": aggregate_severity,
                "priority": "high",
                "title": product_attention_title(
                    risk_type,
                    unique_count,
                ),
                "description": (
                    f"A análise identificou {unique_count} produtos únicos "
                    f"com {label}. Entre os itens de referência estão "
                    f"{', '.join(examples)}."
                ),
                "recommended_action": (
                    "Priorizar os produtos por faturamento, margem e recorrência "
                    "antes de definir ação comercial ou de abastecimento."
                ),
                "entity_type": "product_portfolio",
                "entity_key": risk_type,
                "empresa": None,
                "evidence_text": (
                    f"{unique_count} produtos únicos · "
                    f"{critical_count} críticos"
                ),
                "evidence_value": float(unique_count),
                "sort_order": 0,
                "_impact_score": (
                    unique_count * 1000
                    + critical_count * 5000
                ),
            })

        aggregates.sort(
            key=lambda row: (
                -SEVERITY_RANK[row["severity"]],
                -row["_impact_score"],
                row["title"],
            )
        )

        pools["products"].extend(
            aggregates[:2]
        )

    def _add_profitability_attention(
        self,
        *,
        pools,
        ref,
        period,
        profit_risks,
    ):
        if not profit_risks:
            return

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in profit_risks:
            grouped[
                text(row.get("risk_type"), "profitability_risk")
            ].append(row)

        aggregates = []

        for risk_type, rows in grouped.items():
            total_revenue = sum(
                num(row.get("faturamento"))
                for row in rows
            )
            total_profit = sum(
                num(row.get("lucro"))
                for row in rows
            )
            examples = [
                text(
                    row.get("dimension_value"),
                    row.get("description") or "Dimensão não identificada",
                )
                for row in rows[:3]
            ]
            critical_count = sum(
                1
                for row in rows
                if priority(row.get("priority")) == "critical"
            )

            aggregates.append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "attention",
                    "profitability",
                    "aggregate",
                    risk_type,
                    ref,
                ),
                "source_module": "profitability",
                "attention_type": f"{risk_type}_aggregate",
                "severity": (
                    "critical"
                    if critical_count > 0 or total_profit < 0
                    else "attention"
                ),
                "priority": (
                    "critical"
                    if critical_count > 0
                    else "high"
                ),
                "title": profitability_attention_title(
                    risk_type,
                    len(rows),
                ),
                "description": (
                    f"A análise identificou {len(rows)} dimensões com "
                    f"{risk_label(risk_type)}. Entre as referências estão "
                    f"{', '.join(examples)}."
                ),
                "recommended_action": (
                    "Revisar preço, custo e mix das dimensões de maior impacto "
                    "antes de expandir volume."
                ),
                "entity_type": "profitability_portfolio",
                "entity_key": risk_type,
                "empresa": None,
                "evidence_text": (
                    f"{brl(total_revenue)} de faturamento · "
                    f"{brl(total_profit)} de lucro"
                ),
                "evidence_value": total_profit,
                "sort_order": 0,
                "_impact_score": (
                    abs(total_profit)
                    + abs(total_revenue) * 0.1
                    + critical_count * 100000
                ),
            })

        aggregates.sort(
            key=lambda row: (
                -PRIORITY_RANK[row["priority"]],
                -SEVERITY_RANK[row["severity"]],
                -row["_impact_score"],
            )
        )
        pools["profitability"].extend(aggregates[:2])

    def _add_balanced_stock_attention(
        self,
        *,
        pools,
        ref,
        period,
        stock_risks,
    ):
        if not stock_risks:
            return

        grouped: dict[tuple[str, str], list[dict[str, Any]]] = (
            defaultdict(list)
        )

        for row in stock_risks:
            key = (
                text(row.get("empresa"), "Sem empresa"),
                text(row.get("risk_type"), "stock_risk"),
            )
            grouped[key].append(row)

        aggregate_candidates = []

        for (empresa, risk_type), rows in grouped.items():
            ranked = sorted(
                rows,
                key=lambda row: (
                    -stock_impact(row),
                    -num(row.get("faturamento_90d")),
                    -num(row.get("qtd_vendida_90d")),
                    text(row.get("produto")),
                ),
            )

            top_examples = [
                text(
                    row.get("produto")
                    or row.get("codigo_produto")
                )
                for row in ranked[:3]
            ]

            total_revenue_90d = sum(
                num(row.get("faturamento_90d"))
                for row in rows
            )

            total_qty_90d = sum(
                num(row.get("qtd_vendida_90d"))
                for row in rows
            )

            aggregate_impact = sum(
                stock_impact(row)
                for row in rows
            )

            aggregate_candidates.append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "attention",
                    "stock",
                    "aggregate",
                    empresa,
                    risk_type,
                    ref,
                ),
                "source_module": "stock",
                "attention_type": f"{risk_type}_aggregate",
                "severity": "critical",
                "priority": "critical",
                "title": (
                    f"{risk_type.capitalize()} crítica concentrada "
                    f"em {empresa}"
                ),
                "description": (
                    f"{len(rows)} produtos apresentam {risk_type}. "
                    f"Entre os itens de maior impacto estão "
                    f"{', '.join(top_examples)}."
                ),
                "recommended_action": (
                    "Priorizar os itens de maior faturamento recente, "
                    "avaliar transferência entre filiais e acelerar "
                    "reposição."
                ),
                "entity_type": "stock_portfolio",
                "entity_key": (
                    f"{empresa}|{risk_type}"
                ),
                "empresa": empresa,
                "evidence_text": (
                    f"{len(rows)} itens · "
                    f"{brl(total_revenue_90d)} de faturamento em 90 dias · "
                    f"{int(total_qty_90d)} unidades vendidas"
                ),
                "evidence_value": total_revenue_90d,
                "sort_order": 0,
                "_impact_score": aggregate_impact,
            })

        aggregate_candidates.sort(
            key=lambda row: (
                -row["_impact_score"],
                row["empresa"],
                row["title"],
            )
        )

        # No máximo dois alertas agregados de estoque.
        pools["stock"].extend(
            aggregate_candidates[:2]
        )

        # E no máximo dois produtos individuais, ordenados por impacto real.
        individual_candidates = sorted(
            stock_risks,
            key=lambda row: (
                -stock_impact(row),
                -num(row.get("faturamento_90d")),
                -num(row.get("qtd_vendida_90d")),
                text(row.get("produto")),
            ),
        )

        seen_products = set()

        for row in individual_candidates:
            product_key = text(
                row.get("codigo_produto")
            )

            if not product_key or product_key in seen_products:
                continue

            seen_products.add(product_key)

            revenue_90d = num(
                row.get("faturamento_90d")
            )
            qty_90d = num(
                row.get("qtd_vendida_90d")
            )
            curve = text(
                row.get("curva_abcde"),
                "Sem curva",
            )

            pools["stock"].append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "attention",
                    "stock",
                    row.get("risk_type"),
                    product_key,
                    ref,
                ),
                "source_module": "stock",
                "attention_type": text(
                    row.get("risk_type"),
                    "stock_risk",
                ),
                "severity": severity(
                    row.get("status")
                ),
                "priority": (
                    "critical"
                    if severity(row.get("status")) == "critical"
                    else "high"
                ),
                "title": (
                    "Produto de alto impacto em risco: "
                    f"{text(row.get('produto') or product_key)}"
                ),
                "description": text(
                    row.get("description")
                ),
                "recommended_action": (
                    "Priorizar recomposição, transferência ou "
                    "ação comercial conforme o risco."
                ),
                "entity_type": "product",
                "entity_key": product_key,
                "empresa": row.get("empresa"),
                "evidence_text": (
                    f"Curva {curve} · "
                    f"{brl(revenue_90d)} em 90 dias · "
                    f"{int(qty_90d)} unidades vendidas"
                ),
                "evidence_value": revenue_90d,
                "sort_order": 0,
                "_impact_score": stock_impact(row),
            })

            if len(seen_products) >= 2:
                break

    def _opportunities(
        self,
        ref,
        period,
        commercial,
        stock,
        customers,
        products,
        profitability,
        sellers,
        recs,
        profit_recs,
    ):
        items = []

        def add(
            source,
            kind,
            prio,
            title,
            description,
            action,
            entity_type=None,
            entity_key=None,
            potential=None,
            evidence=None,
        ):
            items.append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "opportunity",
                    source,
                    kind,
                    entity_key or title,
                    ref,
                ),
                "source_module": source,
                "opportunity_type": kind,
                "priority": priority(prio),
                "title": title,
                "description": description,
                "recommended_action": action,
                "entity_type": entity_type,
                "entity_key": entity_key,
                "empresa": None,
                "potential_value": potential,
                "evidence_text": evidence,
                "sort_order": 0,
            })

        excess = integer(
            (stock or {}).get("excesso")
        )

        if excess > 0:
            add(
                "stock",
                "stock_excess_rotation",
                "high",
                "Estoque em excesso pode liberar capital",
                (
                    f"Existem {excess} SKUs classificados "
                    "em excesso."
                ),
                (
                    "Criar campanha de giro conectando excesso, "
                    "margem e carteira com aderência."
                ),
                "stock_portfolio",
                "excess_stock",
                evidence=f"{excess} SKUs em excesso.",
            )

        # Clientes Classe A: usa somente o customer overview consolidado.
        # Recomendações comerciais customer_abc são ignoradas para evitar
        # duplicidade e divergência de granularidade.
        class_a = integer(
            (customers or {}).get("clientes_classe_a")
        )

        if class_a > 0:
            add(
                "customers",
                "protect_class_a",
                "high",
                "Clientes Classe A merecem proteção ativa",
                (
                    f"A base consolidada possui {class_a} "
                    "clientes Classe A."
                ),
                (
                    "Definir rotina de recorrência, ampliação "
                    "de mix e prevenção de inatividade."
                ),
                "customer_tier",
                "A",
                evidence=f"{class_a} clientes Classe A.",
            )

        product_share = num(
            (products or {}).get(
                "top_5_produtos_share"
            )
        )

        if product_share >= 0.40:
            add(
                "products",
                "product_mix_expansion",
                "medium",
                "O mix pode ser ampliado além dos líderes",
                (
                    "Os cinco principais produtos concentram "
                    f"{pct(product_share)} do faturamento."
                ),
                (
                    "Cruzar clientes recorrentes com produtos "
                    "adjacentes de boa margem."
                ),
                "product_portfolio",
                "top_5_concentration",
                evidence=(
                    f"Top 5: {pct(product_share)}."
                ),
            )

        projected = [
            row
            for row in sellers
            if row.get("projecao_atinge_meta")
            and num(
                row.get("projecao_fechamento")
            ) > 0
        ]

        if projected:
            projected_value = sum(
                num(row.get("projecao_fechamento"))
                for row in projected
            )

            add(
                "commercial",
                "seller_projection",
                "medium",
                (
                    "Parte da equipe está projetada "
                    "para atingir a meta"
                ),
                (
                    f"{len(projected)} vendedores estão "
                    "projetados para atingir a meta."
                ),
                (
                    "Preservar o ritmo dos projetados e "
                    "replicar práticas nos demais."
                ),
                "seller_team",
                "projected_to_target",
                projected_value,
                (
                    "Fechamento projetado conjunto: "
                    f"{brl(projected_value)}."
                ),
            )

        margin = num(
            (profitability or {}).get(
                "margem_percentual"
            )
        )

        if margin > 0:
            add(
                "profitability",
                "margin_protection",
                "high" if margin < 20 else "medium",
                (
                    "A margem deve orientar a "
                    "priorização comercial"
                ),
                (
                    "A margem ponderada analisável "
                    f"está em {pt_decimal(margin)}%."
                ),
                (
                    "Priorizar crescimento com produtos e "
                    "clientes que protejam lucro bruto."
                ),
                "metric",
                "weighted_margin",
                num(
                    (profitability or {}).get(
                        "lucro_bruto"
                    )
                ),
                f"Margem atual: {pt_decimal(margin)}%.",
            )

        for row in recs:
            recommendation_type = text(
                row.get("recommendation_type"),
                "commercial_recommendation",
            )

            if recommendation_type == "customer_abc":
                continue

            add(
                "commercial",
                recommendation_type,
                row.get("priority"),
                text(
                    row.get("title"),
                    "Oportunidade comercial",
                ),
                text(row.get("description")),
                text(row.get("description")),
                "commercial",
                text(row.get("id")),
            )

        for row in profit_recs:
            add(
                "profitability",
                text(
                    row.get("recommendation_type"),
                    "profitability_recommendation",
                ),
                row.get("priority"),
                text(
                    row.get("title"),
                    "Oportunidade de rentabilidade",
                ),
                text(row.get("description")),
                text(row.get("action")),
                text(row.get("dimension_type")),
                text(row.get("dimension_key")),
                num(
                    row.get("evidence_value")
                ) or None,
            )

        deduplicated = self._deduplicate_opportunities(
            items
        )

        deduplicated.sort(
            key=lambda row: (
                -PRIORITY_RANK[row["priority"]],
                -abs(
                    num(row.get("potential_value"))
                ),
                row["source_module"],
                row["title"],
            )
        )

        for index, row in enumerate(
            deduplicated,
            1,
        ):
            row["sort_order"] = index

        return deduplicated[:10]

    def _deduplicate_opportunities(
        self,
        items,
    ):
        selected = {}
        semantic_keys = set()

        for row in items:
            semantic_key = (
                row["source_module"],
                row["opportunity_type"],
                text(row.get("entity_key")).lower(),
            )

            title_key = (
                text(row.get("title"))
                .lower()
                .replace("clientes", "cliente")
                .replace("classe a", "class_a")
            )

            if (
                semantic_key in semantic_keys
                or title_key in semantic_keys
            ):
                continue

            semantic_keys.add(semantic_key)
            semantic_keys.add(title_key)
            selected[row["item_key"]] = row

        return list(selected.values())

    def _actions(
        self,
        ref,
        period,
        attention,
        opportunities,
    ):
        candidates = []

        owner_map = {
            "commercial": "Comercial",
            "customers": "Comercial",
            "products": "Comercial",
            "stock": "Suprimentos",
            "profitability": "Diretoria Comercial",
            "lost_sales": "Comercial",
        }

        for row in attention + opportunities:
            action = text(
                row.get("recommended_action")
            )

            if not action:
                continue

            source = row["source_module"]
            kind = (
                row.get("attention_type")
                or row.get("opportunity_type")
            )

            candidates.append({
                "reference_date": ref,
                "period_type": period,
                "item_key": stable_key(
                    "action",
                    source,
                    kind,
                    row.get("entity_key") or row["title"],
                    ref,
                ),
                "source_module": source,
                "priority": row["priority"],
                "action_order": 0,
                "title": row["title"],
                "description": row["description"],
                "action": action,
                "owner_area": owner_map.get(
                    source,
                    "Diretoria",
                ),
                "entity_type": row.get("entity_type"),
                "entity_key": row.get("entity_key"),
                "empresa": row.get("empresa"),
                "expected_impact": row.get(
                    "evidence_text"
                ),
                "evidence_value": (
                    row.get("evidence_value")
                    or row.get("potential_value")
                ),
            })

        unique = {
            row["item_key"]: row
            for row in candidates
        }

        pools = defaultdict(list)

        for row in unique.values():
            pools[row["source_module"]].append(row)

        for rows in pools.values():
            rows.sort(
                key=lambda row: (
                    -PRIORITY_RANK[row["priority"]],
                    -abs(
                        num(row.get("evidence_value"))
                    ),
                    row["title"],
                )
            )

        # Plano de ação também precisa ser multitemático.
        action_quotas = {
            "stock": 2,
            "customers": 2,
            "profitability": 2,
            "commercial": 1,
            "products": 1,
            "lost_sales": 1,
        }

        ordered = []
        leftovers = []

        for source in [
            "stock",
            "customers",
            "profitability",
            "commercial",
            "products",
            "lost_sales",
        ]:
            rows = pools.get(source, [])
            quota = action_quotas.get(source, 0)
            ordered.extend(rows[:quota])
            leftovers.extend(rows[quota:])

        leftovers.sort(
            key=lambda row: (
                -PRIORITY_RANK[row["priority"]],
                -abs(
                    num(row.get("evidence_value"))
                ),
                row["title"],
            )
        )

        if len(ordered) < 8:
            ordered.extend(
                leftovers[: 8 - len(ordered)]
            )

        ordered.sort(
            key=lambda row: (
                -PRIORITY_RANK[row["priority"]],
                -abs(
                    num(row.get("evidence_value"))
                ),
                row["source_module"],
                row["title"],
            )
        )

        ordered = ordered[:8]

        for index, row in enumerate(
            ordered,
            1,
        ):
            row["action_order"] = index

        return ordered

    def _briefing(
        self,
        ref,
        period,
        snapshot,
        commercial,
        stock,
        customers,
        products,
        profitability,
        changes,
        attention,
        opportunities,
        actions,
    ):
        statuses = [
            severity((commercial or {}).get("status")),
            severity((stock or {}).get("status")),
            severity((customers or {}).get("status")),
            severity((products or {}).get("status")),
            severity((profitability or {}).get("status")),
        ]

        overall = max(
            statuses,
            key=lambda value: SEVERITY_RANK[value],
        )

        revenue = num(snapshot.get("faturamento_total"))
        attainment = num(snapshot.get("atingimento_meta_base"))
        ruptures = integer((stock or {}).get("rupturas"))
        customer_risk_count = integer(
            (customers or {}).get("clientes_em_risco")
        )
        product_risk_count = integer(
            (products or {}).get("produtos_em_risco")
        )
        margin = num(
            (profitability or {}).get("margem_percentual")
        )

        revenue_change = next(
            (
                row
                for row in changes
                if row.get("change_type") == "faturamento_total"
            ),
            None,
        )

        revenue_growing = (
            revenue_change is not None
            and num(revenue_change.get("variation_value")) > 0
        )

        critical_modules = sum(
            1
            for status_value in statuses
            if status_value == "critical"
        )

        executive_score = self._executive_score(
            statuses=statuses,
            attainment=attainment,
            ruptures=ruptures,
            customer_risk_count=customer_risk_count,
            product_risk_count=product_risk_count,
            margin=margin,
        )
        executive_score_label = self._executive_score_label(executive_score)

        if revenue_growing and overall in {"attention", "critical"}:
            headline = (
                "A operação cresce em faturamento, mas a qualidade "
                "do resultado exige atenção."
            )
        elif overall == "critical":
            headline = (
                "A operação exige intervenção executiva imediata "
                "para proteger receita e margem."
            )
        elif overall == "attention":
            headline = (
                "A operação mantém atividade, porém sinais relevantes "
                "podem comprometer o fechamento."
            )
        elif overall == "monitoring":
            headline = (
                "A operação permanece estável, com pontos específicos "
                "que precisam de acompanhamento."
            )
        else:
            headline = (
                "A operação apresenta condição geral saudável e "
                "o foco deve permanecer em sustentar o ritmo."
            )

        narrative_parts = []

        if revenue_growing:
            narrative_parts.append(
                "O avanço comercial é positivo"
            )
        else:
            narrative_parts.append(
                f"O faturamento acumulado é de {brl(revenue)}"
            )

        if attainment < 1:
            narrative_parts.append(
                f"o atingimento da meta está em {pct(attainment)}"
            )

        pressure_parts = []

        if ruptures > 0:
            pressure_parts.append(
                f"{ruptures} rupturas de estoque"
            )

        if customer_risk_count > 0:
            pressure_parts.append(
                f"{customer_risk_count} clientes em risco"
            )

        if product_risk_count > 0:
            pressure_parts.append(
                f"{product_risk_count} produtos sob pressão"
            )

        if margin > 0:
            pressure_parts.append(
                f"margem ponderada de {pt_decimal(margin)}%"
            )

        summary = ", porém ".join(narrative_parts)

        if pressure_parts:
            summary += (
                ". A qualidade do resultado está pressionada por "
                + ", ".join(pressure_parts[:-1])
                + (
                    " e " + pressure_parts[-1]
                    if len(pressure_parts) > 1
                    else pressure_parts[0]
                )
            )

        if critical_modules > 0:
            summary += (
                f". {critical_modules} frente"
                f"{'s estão' if critical_modules > 1 else ' está'} "
                "em condição crítica"
            )

        summary += (
            ". A prioridade é proteger disponibilidade, recuperar "
            "receita exposta e concentrar crescimento nas frentes "
            "que preservam margem."
        )

        return {
            "reference_date": ref,
            "period_type": period,
            "scope_key": "all",
            "empresa": None,
            "overall_status": overall,
            "headline": headline,
            "summary": summary,
            "change_count": len(changes),
            "attention_count": len(attention),
            "opportunity_count": len(opportunities),
            "action_count": len(actions),
            "source_count": 5,
            "executive_score": executive_score,
            "executive_score_label": executive_score_label,
        }

    def _executive_score(
        self,
        statuses,
        attainment,
        ruptures,
        customer_risk_count,
        product_risk_count,
        margin,
    ):
        """Score executivo determinístico de 0 a 100, calculado no backend."""
        score = 100.0

        status_penalty = {
            "healthy": 0.0,
            "monitoring": 4.0,
            "attention": 10.0,
            "critical": 18.0,
        }
        score -= sum(status_penalty.get(value, 4.0) for value in statuses)

        if attainment > 0:
            score -= max(0.0, min(18.0, (1.0 - attainment) * 18.0))

        score -= min(15.0, ruptures / 30.0)
        score -= min(8.0, customer_risk_count / 4.0)
        score -= min(8.0, product_risk_count / 10.0)

        if margin > 0:
            if margin < 20:
                score -= 12.0
            elif margin < 30:
                score -= 8.0
            elif margin < 40:
                score -= 4.0

        return round(max(0.0, min(100.0, score)), 1)

    def _executive_score_label(self, score):
        if score >= 85:
            return "Saudável"
        if score >= 70:
            return "Estável"
        if score >= 55:
            return "Atenção"
        return "Crítico"

    def _events(
        self,
        ref,
        period,
        changes,
        attention,
        opportunities,
    ):
        events = []

        source_rows = (
            changes
            + attention[:5]
            + opportunities[:3]
        )

        for row in source_rows:
            source = row["source_module"]

            event_type = (
                row.get("change_type")
                or row.get("attention_type")
                or row.get("opportunity_type")
            )

            sev = (
                row.get("severity")
                or "monitoring"
            )

            metric = (
                row.get("current_value")
                or row.get("evidence_value")
                or row.get("potential_value")
            )

            events.append({
                "event_key": stable_key(
                    ref,
                    period,
                    source,
                    event_type,
                    row.get("entity_key") or row["title"],
                ),
                "event_date": ref,
                "reference_date": ref,
                "period_type": period,
                "source_module": source,
                "event_type": event_type,
                "severity": severity(sev),
                "title": row["title"],
                "description": row["description"],
                "entity_type": row.get("entity_type"),
                "entity_key": row.get("entity_key"),
                "empresa": row.get("empresa"),
                "metric_name": event_type,
                "metric_value": metric,
                "metadata": {
                    "priority": row.get("priority"),
                    "direction": row.get("direction"),
                    "recommended_action": row.get(
                        "recommended_action"
                    ),
                },
            })

        return events
