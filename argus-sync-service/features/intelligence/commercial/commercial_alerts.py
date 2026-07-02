class CommercialAlerts:

    def build(self, concentration_records):

        alerts = []

        concentration_records = concentration_records or []

        for record in concentration_records:

            if record["concentration_type"] == "customer" and record["top_n"] == 5:
                if record["participation"] >= 0.60:
                    alerts.append({
                        "alert_type": "customer_concentration",
                        "severity": "high",
                        "title": "Alta concentração de clientes",
                        "description": record["description"]
                    })

            if record["concentration_type"] == "product" and record["top_n"] == 5:
                if record["participation"] >= 0.60:
                    alerts.append({
                        "alert_type": "product_concentration",
                        "severity": "medium",
                        "title": "Concentração em produtos",
                        "description": record["description"]
                    })

        if not alerts:
            alerts.append({
                "alert_type": "commercial_health",
                "severity": "low",
                "title": "Nenhum alerta crítico comercial",
                "description": "Os indicadores comerciais atuais não apontam concentração crítica acima dos limites definidos."
            })

        return alerts