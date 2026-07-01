class SellerRanking:

    def normalize_name(self, name):
        particles = {"de", "da", "do", "das", "dos", "e"}

        words = str(name).strip().lower().split()

        formatted_words = [
            word if word in particles else word.capitalize()
            for word in words
        ]

        return " ".join(formatted_words)

    def build(self, pedidos_df):

        df = pedidos_df.copy()

        df["Vendedor"] = df["Vendedor"].apply(self.normalize_name)
        df["Empresa"] = df["Empresa"].apply(lambda x: str(x).strip())

        total_ranking = (
            df
            .groupby("Vendedor")
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                itens_vendidos=("codigo_item", "count"),
                clientes=("codigo_cliente", "nunique")
            )
            .reset_index()
        )

        total_ranking["ticket_medio"] = (
            total_ranking["faturamento_total"] / total_ranking["pedidos"]
        )

        empresa_ranking = (
            df
            .groupby(["Vendedor", "Empresa"])
            .agg(
                faturamento_total=("Valor_total_Unitario", "sum"),
                pedidos=("numero_pedido", "nunique"),
                itens_vendidos=("codigo_item", "count"),
                clientes=("codigo_cliente", "nunique")
            )
            .reset_index()
        )

        breakdown_map = {}

        for vendedor, grupo in empresa_ranking.groupby("Vendedor"):
            breakdown_map[vendedor] = []

            for _, row in grupo.iterrows():
                breakdown_map[vendedor].append({
                    "empresa": row["Empresa"],
                    "faturamento_total": round(float(row["faturamento_total"]), 2),
                    "pedidos": int(row["pedidos"]),
                    "itens_vendidos": int(row["itens_vendidos"]),
                    "clientes": int(row["clientes"])
                })

        total_ranking["empresa_breakdown"] = total_ranking["Vendedor"].map(breakdown_map)

        return total_ranking.sort_values(
            by="faturamento_total",
            ascending=False
        )