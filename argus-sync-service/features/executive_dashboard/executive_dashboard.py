from services.sales_metrics import SalesMetrics


class ExecutiveDashboard:

    def __init__(self):
        self.sales = SalesMetrics()

    def build(self, pedidos_df, metas_df=None):

        faturamento_total = self.sales.total_revenue(pedidos_df)

        data = {
            "faturamento_total": faturamento_total,
            "pedidos": len(pedidos_df),
            "clientes": pedidos_df["codigo_cliente"].nunique(),
            "ticket_medio": faturamento_total / len(pedidos_df) if len(pedidos_df) > 0 else 0,
        }

        if metas_df is not None and len(metas_df) > 0:
            meta_base = metas_df["meta_base"].sum()
            super_meta = metas_df["super_meta"].sum()
            hiper_meta = metas_df["hiper_meta"].sum()

            data.update({
                "meta_base": meta_base,
                "super_meta": super_meta,
                "hiper_meta": hiper_meta,
                "atingimento_meta_base": faturamento_total / meta_base if meta_base > 0 else 0,
                "atingimento_super_meta": faturamento_total / super_meta if super_meta > 0 else 0,
                "atingimento_hiper_meta": faturamento_total / hiper_meta if hiper_meta > 0 else 0,
            })

        return data