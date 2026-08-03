from features.sales.seller_performance import SellerPerformance


class SellerRanking:

    def __init__(self):

        self.performance = SellerPerformance()

    def build(self, pedidos_df):

        ranking = self.performance.build(pedidos_df)

        return ranking.sort_values(
            by="faturamento_total",
            ascending=False
        )