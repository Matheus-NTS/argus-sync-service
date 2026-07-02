class ConcentrationAnalysis:

    def build(self, customer_df, product_df):

        records = []

        records.extend(
            self._calculate_concentration(
                df=customer_df,
                value_column="faturamento_total",
                concentration_type="customer",
                label="clientes"
            )
        )

        records.extend(
            self._calculate_concentration(
                df=product_df,
                value_column="faturamento_total",
                concentration_type="product",
                label="produtos"
            )
        )

        return records

    def _calculate_concentration(self, df, value_column, concentration_type, label):

        results = []

        if df is None or len(df) == 0:
            return results

        total = df[value_column].sum()

        if total <= 0:
            return results

        ordered = df.sort_values(
            by=value_column,
            ascending=False
        ).reset_index(drop=True)

        for top_n in [3, 5, 10]:

            top_value = ordered.head(top_n)[value_column].sum()
            participation = top_value / total

            results.append({
                "concentration_type": concentration_type,
                "top_n": top_n,
                "participation": participation,
                "description": (
                    f"Os top {top_n} {label} representam "
                    f"{participation:.2%} do faturamento do mês."
                )
            })

        return results