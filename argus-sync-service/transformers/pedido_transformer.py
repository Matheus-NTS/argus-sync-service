
class PedidoTransformer:

    def __init__(self, valid_status=None):
        self.valid_status = valid_status or ["CONCRETIZADO"]

    def filter_revenue_orders(self, pedidos_df):

        pedidos = pedidos_df.copy()

        situacao_normalizada = (
            pedidos["situacao"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        valid_status = {
            str(status).strip().upper()
            for status in self.valid_status
        }

        return pedidos[
            situacao_normalizada.isin(valid_status)
        ].copy()