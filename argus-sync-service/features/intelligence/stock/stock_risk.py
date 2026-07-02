class StockRisk:

    def build(self, stock_df):

        risks = []

        risk_df = stock_df[stock_df["status"].isin(["critical", "attention"])].copy()

        for _, row in risk_df.iterrows():

            risk_type = row["risk_type"]

            if risk_type == "ruptura":
                description = (
                    "Produto com estoque zerado e venda nos últimos 90 dias. "
                    "Risco de ruptura comercial."
                )

            elif risk_type == "curva_a_critico":
                description = (
                    "Produto de curva A em situação crítica de estoque. "
                    "Recomenda-se priorizar reposição."
                )

            elif risk_type == "sem_giro":
                description = (
                    "Produto com estoque disponível, mas sem venda recente. "
                    "Avaliar ação comercial ou revisão de compra."
                )

            elif risk_type == "excesso":
                description = (
                    "Produto com cobertura de estoque elevada. "
                    "Avaliar excesso, capital imobilizado e necessidade de campanha."
                )

            else:
                description = "Produto exige acompanhamento de estoque."

            risks.append({
                "codigo_produto": str(row["codigo_produto"]),
                "produto": row["Descricao"],
                "empresa": row["Empresa"],
                "curva_abcde": row["Curva_ABCDE"],
                "estoque_atual": row["Quantidade_Estoque"],
                "valor_estoque": row["valor_estoque"],
                "qtd_vendida_90d": row["qtd_vendida_90d"],
                "faturamento_90d": row["faturamento_90d"],
                "ultima_venda": row["ultima_venda"],
                "dias_sem_venda": row["dias_sem_venda"],
                "cobertura_estoque": row["cobertura_estoque"],
                "risk_type": risk_type,
                "status": row["status"],
                "description": description
            })

        return risks