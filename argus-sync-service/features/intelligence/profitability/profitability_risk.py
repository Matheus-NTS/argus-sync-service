class ProfitabilityRisk:

    def build(self, dimensions, overview):

        risks = []

        products = dimensions.get("product", [])
        customers = dimensions.get("customer", [])
        sellers = dimensions.get("seller", [])
        categories = dimensions.get("category", [])

        for item in products:

            margem = item.get("margem_percentual")
            lucro = item.get("lucro", 0)
            faturamento = item.get("faturamento", 0)

            if lucro < 0:
                risks.append({
                    "risk_type": "product_loss",
                    "dimension_type": "product",
                    "dimension_key": item["dimension_key"],
                    "dimension_value": item["dimension_value"],
                    "priority": "high",
                    "faturamento": faturamento,
                    "lucro": lucro,
                    "margem_percentual": margem,
                    "description": (
                        "Produto com lucro bruto negativo no período."
                    ),
                    "recommended_action": (
                        "Revisar preço praticado, custo cadastrado, "
                        "descontos e possíveis anomalias de quantidade."
                    ),
                })

            elif margem is not None and margem < 5:
                risks.append({
                    "risk_type": "product_critical_margin",
                    "dimension_type": "product",
                    "dimension_key": item["dimension_key"],
                    "dimension_value": item["dimension_value"],
                    "priority": "high",
                    "faturamento": faturamento,
                    "lucro": lucro,
                    "margem_percentual": margem,
                    "description": (
                        "Produto com margem bruta consolidada abaixo de 5%."
                    ),
                    "recommended_action": (
                        "Revisar tabela de preços, política de desconto "
                        "e viabilidade comercial."
                    ),
                })

            elif (
                margem is not None
                and margem < 10
                and item.get("participacao_faturamento", 0) >= 0.01
            ):
                risks.append({
                    "risk_type": "product_low_margin_high_revenue",
                    "dimension_type": "product",
                    "dimension_key": item["dimension_key"],
                    "dimension_value": item["dimension_value"],
                    "priority": "medium",
                    "faturamento": faturamento,
                    "lucro": lucro,
                    "margem_percentual": margem,
                    "description": (
                        "Produto relevante em faturamento, mas com margem baixa."
                    ),
                    "recommended_action": (
                        "Avaliar reajuste, renegociação de custo "
                        "ou mudança no mix comercial."
                    ),
                })

        average_margin = overview.get("margem_percentual", 0)

        for item in customers:

            margem = item.get("margem_percentual")
            faturamento = item.get("faturamento", 0)

            if (
                margem is not None
                and margem < (average_margin - 10)
                and item.get("participacao_faturamento", 0) >= 0.02
            ):
                risks.append({
                    "risk_type": "customer_low_profitability",
                    "dimension_type": "customer",
                    "dimension_key": item["dimension_key"],
                    "dimension_value": item["dimension_value"],
                    "priority": "medium",
                    "faturamento": faturamento,
                    "lucro": item.get("lucro", 0),
                    "margem_percentual": margem,
                    "description": (
                        "Cliente relevante em faturamento com margem "
                        "significativamente abaixo da média."
                    ),
                    "recommended_action": (
                        "Revisar descontos, condições comerciais "
                        "e mix de produtos do cliente."
                    ),
                })

        for item in sellers:

            margem = item.get("margem_percentual")

            if (
                margem is not None
                and margem < (average_margin - 8)
                and item.get("participacao_faturamento", 0) >= 0.03
            ):
                risks.append({
                    "risk_type": "seller_margin_below_average",
                    "dimension_type": "seller",
                    "dimension_key": item["dimension_key"],
                    "dimension_value": item["dimension_value"],
                    "priority": "medium",
                    "faturamento": item.get("faturamento", 0),
                    "lucro": item.get("lucro", 0),
                    "margem_percentual": margem,
                    "description": (
                        "Concentração de vendas com margem abaixo "
                        "da média da operação."
                    ),
                    "recommended_action": (
                        "Analisar mix vendido, descontos e produtos "
                        "mais recorrentes."
                    ),
                })

        for item in categories:

            margem = item.get("margem_percentual")

            if (
                margem is not None
                and margem < 10
                and item.get("participacao_faturamento", 0) >= 0.03
            ):
                risks.append({
                    "risk_type": "category_low_margin",
                    "dimension_type": "category",
                    "dimension_key": item["dimension_key"],
                    "dimension_value": item["dimension_value"],
                    "priority": "high",
                    "faturamento": item.get("faturamento", 0),
                    "lucro": item.get("lucro", 0),
                    "margem_percentual": margem,
                    "description": (
                        "Categoria relevante com margem consolidada baixa."
                    ),
                    "recommended_action": (
                        "Revisar produtos líderes, custos e política "
                        "comercial da categoria."
                    ),
                })

        priority_order = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }

        risks.sort(
            key=lambda item: (
                priority_order.get(item["priority"], 9),
                item.get("lucro", 0),
            )
        )

        return risks