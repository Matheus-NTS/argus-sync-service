class ABCAnalysis:

    def build(self, product_df):

        df = product_df.copy()

        df = df.sort_values(
            by="faturamento_total",
            ascending=False
        ).reset_index(drop=True)

        total = df["faturamento_total"].sum()

        if total <= 0:
            return df

        df["percentual"] = df["faturamento_total"] / total
        df["percentual_acumulado"] = df["percentual"].cumsum()
        df["ranking"] = df.index + 1

        def classify(value):
            if value <= 0.80:
                return "A"
            if value <= 0.95:
                return "B"
            return "C"

        df["classe"] = df["percentual_acumulado"].apply(classify)

        return df