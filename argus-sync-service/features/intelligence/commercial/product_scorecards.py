class ProductScorecards:

    def build(self, product_overview):

        return [
            {
                "card_key": "produtos_ativos",
                "label": "Produtos Ativos",
                "value_numeric": product_overview["produtos_ativos"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 1
            },
            {
                "card_key": "produtos_classe_a",
                "label": "Produtos Classe A",
                "value_numeric": product_overview["produtos_classe_a"],
                "value_text": None,
                "value_type": "number",
                "status": product_overview["status"],
                "sort_order": 2
            },
            {
                "card_key": "produtos_em_risco",
                "label": "Produtos em Risco",
                "value_numeric": product_overview["produtos_em_risco"],
                "value_text": None,
                "value_type": "number",
                "status": product_overview["status"],
                "sort_order": 3
            },
            {
                "card_key": "faturamento_total_produtos",
                "label": "Faturamento Produtos",
                "value_numeric": product_overview["faturamento_total"],
                "value_text": None,
                "value_type": "currency",
                "status": "neutral",
                "sort_order": 4
            },
            {
                "card_key": "top_produto_faturamento",
                "label": "Top Produto",
                "value_numeric": product_overview["top_produto_faturamento"],
                "value_text": product_overview["top_produto"],
                "value_type": "currency_with_label",
                "status": "neutral",
                "sort_order": 5
            },
            {
                "card_key": "top_5_produtos_share",
                "label": "Top 5 Produtos",
                "value_numeric": product_overview["top_5_produtos_share"],
                "value_text": None,
                "value_type": "percentage",
                "status": product_overview["status"],
                "sort_order": 6
            }
        ]