class SalesMetrics:
    def __init__(self, value_column="Valor_total_Unitario"):
        self.value_column = value_column

    def total_revenue(self, pedidos_df):
        return pedidos_df[self.value_column].sum()