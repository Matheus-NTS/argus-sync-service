class CategoryScorecards:

    def build(self, category_overview):

        return [
            {
                "card_key": "categorias_ativas",
                "label": "Categorias Ativas",
                "value_numeric": category_overview["categorias_ativas"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 1
            },
            {
                "card_key": "faturamento_total_categorias",
                "label": "Faturamento Categorias",
                "value_numeric": category_overview["faturamento_total"],
                "value_text": None,
                "value_type": "currency",
                "status": "neutral",
                "sort_order": 2
            },
            {
                "card_key": "top_categoria_faturamento",
                "label": "Top Categoria",
                "value_numeric": category_overview["top_categoria_faturamento"],
                "value_text": category_overview["top_categoria"],
                "value_type": "currency_with_label",
                "status": "neutral",
                "sort_order": 3
            },
            {
                "card_key": "produtos_total_categoria",
                "label": "Produtos nas Categorias",
                "value_numeric": category_overview["produtos_total"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 4
            },
            {
                "card_key": "clientes_total_categoria",
                "label": "Clientes nas Categorias",
                "value_numeric": category_overview["clientes_total"],
                "value_text": None,
                "value_type": "number",
                "status": "neutral",
                "sort_order": 5
            }
        ]