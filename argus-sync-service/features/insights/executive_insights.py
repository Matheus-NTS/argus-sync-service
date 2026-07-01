class ExecutiveInsights:

    def build(self, dashboard_data, ranking_df=None):

        insights = []

        atingimento = dashboard_data["atingimento_meta_base"]
        faturamento = dashboard_data["faturamento_total"]
        meta_base = dashboard_data["meta_base"]
        super_meta = dashboard_data["super_meta"]
        hiper_meta = dashboard_data["hiper_meta"]

        if atingimento >= 1:
            insights.append({
                "insight_type": "goal",
                "severity": "success",
                "title": "Meta Base atingida",
                "description": f"A empresa atingiu {atingimento:.2%} da Meta Base no mês."
            })
        else:
            gap = meta_base - faturamento
            insights.append({
                "insight_type": "goal",
                "severity": "warning",
                "title": "Meta Base ainda não atingida",
                "description": f"Faltam R$ {gap:,.2f} para atingir a Meta Base do mês."
            })

        gap_super = super_meta - faturamento
        if gap_super > 0:
            insights.append({
                "insight_type": "goal",
                "severity": "info",
                "title": "Distância para a Super Meta",
                "description": f"Faltam R$ {gap_super:,.2f} para atingir a Super Meta."
            })

        gap_hiper = hiper_meta - faturamento
        if gap_hiper > 0:
            insights.append({
                "insight_type": "goal",
                "severity": "info",
                "title": "Distância para a Hiper Meta",
                "description": f"Faltam R$ {gap_hiper:,.2f} para atingir a Hiper Meta."
            })

        if ranking_df is not None and len(ranking_df) > 0:
            top_seller = ranking_df.iloc[0]
            insights.append({
                "insight_type": "seller",
                "severity": "success",
                "title": "Vendedor destaque",
                "description": (
                    f"{top_seller['Vendedor']} lidera o mês com "
                    f"R$ {top_seller['faturamento_total']:,.2f} em faturamento."
                )
            })

        ticket = dashboard_data["ticket_medio"]
        insights.append({
            "insight_type": "sales",
            "severity": "info",
            "title": "Ticket médio do mês",
            "description": f"O ticket médio atual está em R$ {ticket:,.2f}."
        })

        return insights