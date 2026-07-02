class StockScorecards:

    def build(self, overview):

        return [
            {
                "card_key": "sku_total",
                "label": "SKUs Analisados",
                "value_numeric": overview["sku_total"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 1
            },
            {
                "card_key": "valor_total_estoque",
                "label": "Valor em Estoque",
                "value_numeric": overview["valor_total_estoque"],
                "value_text": None,
                "value_type": "currency",
                "status": overview["status"],
                "sort_order": 2
            },
            {
                "card_key": "sku_criticos",
                "label": "Itens Críticos",
                "value_numeric": overview["sku_criticos"],
                "value_text": None,
                "value_type": "number",
                "status": "critical" if overview["sku_criticos"] > 0 else "healthy",
                "sort_order": 3
            },
            {
                "card_key": "sku_atencao",
                "label": "Itens em Atenção",
                "value_numeric": overview["sku_atencao"],
                "value_text": None,
                "value_type": "number",
                "status": "attention" if overview["sku_atencao"] > 0 else "healthy",
                "sort_order": 4
            },
            {
                "card_key": "rupturas",
                "label": "Rupturas",
                "value_numeric": overview["rupturas"],
                "value_text": None,
                "value_type": "number",
                "status": "critical" if overview["rupturas"] > 0 else "healthy",
                "sort_order": 5
            },
            {
                "card_key": "sem_giro",
                "label": "Sem Giro",
                "value_numeric": overview["sem_giro"],
                "value_text": None,
                "value_type": "number",
                "status": "attention" if overview["sem_giro"] > 0 else "healthy",
                "sort_order": 6
            },
            {
                "card_key": "excesso",
                "label": "Excesso",
                "value_numeric": overview["excesso"],
                "value_text": None,
                "value_type": "number",
                "status": "attention" if overview["excesso"] > 0 else "healthy",
                "sort_order": 7
            }
        ]