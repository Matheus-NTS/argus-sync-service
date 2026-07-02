class CustomerScorecards:

    def build(self, customer_overview):

        return [
            {
                "card_key": "clientes_ativos",
                "label": "Clientes Ativos",
                "value_numeric": customer_overview["clientes_ativos"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 1
            },
            {
                "card_key": "clientes_classe_a",
                "label": "Clientes Classe A",
                "value_numeric": customer_overview["clientes_classe_a"],
                "value_text": None,
                "value_type": "number",
                "status": customer_overview["status"],
                "sort_order": 2
            },
            {
                "card_key": "clientes_em_risco",
                "label": "Clientes em Risco",
                "value_numeric": customer_overview["clientes_em_risco"],
                "value_text": None,
                "value_type": "number",
                "status": customer_overview["status"],
                "sort_order": 3
            },
            {
                "card_key": "faturamento_total_clientes",
                "label": "Faturamento Clientes",
                "value_numeric": customer_overview["faturamento_total"],
                "value_text": None,
                "value_type": "currency",
                "status": "neutral",
                "sort_order": 4
            },
            {
                "card_key": "top_cliente_faturamento",
                "label": "Top Cliente",
                "value_numeric": customer_overview["top_cliente_faturamento"],
                "value_text": customer_overview["top_cliente"],
                "value_type": "currency_with_label",
                "status": "neutral",
                "sort_order": 5
            },
            {
                "card_key": "top_5_clientes_share",
                "label": "Top 5 Clientes",
                "value_numeric": customer_overview["top_5_clientes_share"],
                "value_text": None,
                "value_type": "percentage",
                "status": customer_overview["status"],
                "sort_order": 6
            }
        ]