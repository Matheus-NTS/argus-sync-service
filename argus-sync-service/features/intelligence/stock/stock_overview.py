class StockOverview:

    def build(self, stock_df):

        sku_total = len(stock_df)

        sku_criticos = len(stock_df[stock_df["status"] == "critical"])
        sku_atencao = len(stock_df[stock_df["status"] == "attention"])
        sku_saudaveis = len(stock_df[stock_df["status"] == "healthy"])

        valor_total_estoque = float(stock_df["valor_estoque"].sum()) if sku_total > 0 else 0
        quantidade_total_estoque = float(stock_df["Quantidade_Estoque"].sum()) if sku_total > 0 else 0

        rupturas = len(stock_df[stock_df["risk_type"] == "ruptura"])
        sem_giro = len(stock_df[stock_df["risk_type"] == "sem_giro"])
        excesso = len(stock_df[stock_df["risk_type"] == "excesso"])

        if sku_criticos >= 200:
            status = "critical"
        elif sku_criticos >= 100 or sku_atencao >= 300:
            status = "attention"
        elif sku_criticos > 0 or sku_atencao > 0:
            status = "monitoring"
        else:
            status = "healthy"

        headline = (
            f"O estoque possui {sku_total} produtos analisados, "
            f"com {sku_criticos} itens críticos, {sku_atencao} em atenção "
            f"e valor total estimado de R$ {valor_total_estoque:,.2f}."
        )

        return {
            "sku_total": sku_total,
            "sku_criticos": sku_criticos,
            "sku_atencao": sku_atencao,
            "sku_saudaveis": sku_saudaveis,
            "valor_total_estoque": valor_total_estoque,
            "quantidade_total_estoque": quantidade_total_estoque,
            "rupturas": rupturas,
            "sem_giro": sem_giro,
            "excesso": excesso,
            "headline": headline,
            "status": status
        }