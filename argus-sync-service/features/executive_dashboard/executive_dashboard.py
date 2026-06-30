from services.sales_metrics import SalesMetrics


class ExecutiveDashboard:

    def __init__(self):
        self.sales = SalesMetrics()

    def build(self, pedidos_df):

        return {
            "faturamento_total": self.sales.total_revenue(pedidos_df),

            "pedidos": len(pedidos_df),

            "clientes": pedidos_df["codigo_cliente"].nunique(),

            "ticket_medio":
                self.sales.total_revenue(pedidos_df) /
                len(pedidos_df)
                if len(pedidos_df) > 0 else 0
        }