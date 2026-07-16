import pandas as pd


class ProfitabilityQuality:

    STATUS_DESCRIPTIONS = {
        "analisavel": (
            "Registro elegível para os indicadores oficiais de "
            "faturamento, custo, lucro, margem e markup."
        ),
        "sem_custo_valido": (
            "Venda de produto sem custo válido no cadastro atual."
        ),
        "dado_suspeito": (
            "Registro com possível anomalia financeira, como margem "
            "extremamente negativa ou preço muito inferior ao custo."
        ),
        "produto_fora_escopo": (
            "Registro relacionado a treinamento, serviço, teste ou "
            "cadastro sem descrição válida de produto."
        ),
        "empresa_fora_escopo": (
            "Registro pertencente a empresa fora do escopo oficial "
            "da análise de Rentabilidade."
        ),
    }

    STATUS_ORDER = [
        "analisavel",
        "sem_custo_valido",
        "dado_suspeito",
        "produto_fora_escopo",
        "empresa_fora_escopo",
    ]

    def build(self, dataset):

        total_revenue = float(
            dataset["faturamento"].sum()
        )

        records = []

        for analysis_status in self.STATUS_ORDER:

            status_df = dataset[
                dataset["status_analise"]
                == analysis_status
            ].copy()

            revenue = float(
                status_df["faturamento"].sum()
            )

            participation = (
                revenue / total_revenue
                if total_revenue > 0
                else 0
            )

            records.append({
                "analysis_status": analysis_status,
                "linhas": int(len(status_df)),
                "pedidos": int(
                    status_df["numero_pedido"].nunique()
                ),
                "produtos": int(
                    status_df["codigo_produto"].nunique()
                ),
                "clientes": int(
                    status_df[
                        "codigo_cliente_normalizado"
                    ].nunique()
                ),
                "faturamento": round(
                    revenue,
                    2
                ),
                "participacao_faturamento": round(
                    participation,
                    8
                ),
                "description": (
                    self.STATUS_DESCRIPTIONS[
                        analysis_status
                    ]
                ),
            })

        return records