class PedidoTransformer:
    def __init__(self, valid_status=None):
        self.valid_status = valid_status or ["CONCRETIZADO"]

    def filter_revenue_orders(self, pedidos_df):
        pedidos_filtrados = pedidos_df[
            pedidos_df["situacao"].str.upper().isin(self.valid_status)
        ].copy()

        return pedidos_filtrados