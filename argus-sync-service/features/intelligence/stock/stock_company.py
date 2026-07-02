class StockCompany:

    def build(self, stock_df):

        company_records = []

        grouped = stock_df.groupby("Empresa", dropna=False)

        for empresa, df_empresa in grouped:

            empresa_nome = empresa
            if empresa_nome is None or str(empresa_nome).strip() == "":
                empresa_nome = "Não informado"

            sku_total = len(df_empresa)
            sku_criticos = len(df_empresa[df_empresa["status"] == "critical"])
            sku_atencao = len(df_empresa[df_empresa["status"] == "attention"])
            sku_saudaveis = len(df_empresa[df_empresa["status"] == "healthy"])

            quantidade_total_estoque = float(df_empresa["Quantidade_Estoque"].sum()) if sku_total > 0 else 0
            valor_total_estoque = float(df_empresa["valor_estoque"].sum()) if sku_total > 0 else 0

            rupturas = len(df_empresa[df_empresa["risk_type"] == "ruptura"])
            sem_giro = len(df_empresa[df_empresa["risk_type"] == "sem_giro"])
            excesso = len(df_empresa[df_empresa["risk_type"] == "excesso"])

            if sku_criticos >= 80:
                status = "critical"
            elif sku_criticos >= 30 or sku_atencao >= 80:
                status = "attention"
            elif sku_criticos > 0 or sku_atencao > 0:
                status = "monitoring"
            else:
                status = "healthy"

            company_records.append({
                "empresa": str(empresa_nome),
                "sku_total": int(sku_total),
                "sku_criticos": int(sku_criticos),
                "sku_atencao": int(sku_atencao),
                "sku_saudaveis": int(sku_saudaveis),
                "quantidade_total_estoque": round(float(quantidade_total_estoque), 2),
                "valor_total_estoque": round(float(valor_total_estoque), 2),
                "rupturas": int(rupturas),
                "sem_giro": int(sem_giro),
                "excesso": int(excesso),
                "status": status
            })

        company_records = sorted(
            company_records,
            key=lambda x: x["valor_total_estoque"],
            reverse=True
        )

        return company_records