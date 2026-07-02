class CommercialScorecards:

    def build(self, overview):

        return [
            {
                "card_key": "faturamento_total",
                "label": "Faturamento Total",
                "value_numeric": overview["faturamento_total"],
                "value_text": None,
                "value_type": "currency",
                "status": overview["status"],
                "sort_order": 1
            },
            {
                "card_key": "clientes_ativos",
                "label": "Clientes Ativos",
                "value_numeric": overview["clientes_ativos"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 2
            },
            {
                "card_key": "produtos_ativos",
                "label": "Produtos Ativos",
                "value_numeric": overview["produtos_ativos"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 3
            },
            {
                "card_key": "ticket_medio",
                "label": "Ticket Médio",
                "value_numeric": overview["ticket_medio"],
                "value_text": None,
                "value_type": "currency",
                "status": "neutral",
                "sort_order": 4
            },
            {
                "card_key": "riscos_comerciais",
                "label": "Riscos Comerciais",
                "value_numeric": overview["customer_risks_count"] + overview["product_risks_count"],
                "value_text": None,
                "value_type": "number",
                "status": overview["status"],
                "sort_order": 5
            },
            {
                "card_key": "alertas_comerciais",
                "label": "Alertas Comerciais",
                "value_numeric": overview["alertas_count"],
                "value_text": None,
                "value_type": "number",
                "status": overview["status"],
                "sort_order": 6
            },
            {
                "card_key": "top_5_clientes_share",
                "label": "Top 5 Clientes",
                "value_numeric": overview["top_5_clientes_share"],
                "value_text": None,
                "value_type": "percentage",
                "status": overview["status"],
                "sort_order": 7
            },
            {
                "card_key": "top_5_produtos_share",
                "label": "Top 5 Produtos",
                "value_numeric": overview["top_5_produtos_share"],
                "value_text": None,
                "value_type": "percentage",
                "status": overview["status"],
                "sort_order": 8
            }
        ]