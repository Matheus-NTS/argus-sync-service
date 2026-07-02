from datetime import datetime

import pandas as pd


class StockSnapshot:

    def normalize_company(self, value):

        if pd.isna(value):
            return None

        raw = str(value).strip().upper()

        raw = (
            raw
            .replace("Ã", "A")
            .replace("Á", "A")
            .replace("À", "A")
            .replace("Â", "A")
            .replace("É", "E")
            .replace("Ê", "E")
            .replace("Í", "I")
            .replace("Ó", "O")
            .replace("Ô", "O")
            .replace("Ú", "U")
            .replace("Ç", "C")
        )

        raw = " ".join(raw.split())

        mapping = {
            "NTS RIO": "NTS RIO DE JANEIRO",
            "NTS RIO DE JANEIRO": "NTS RIO DE JANEIRO",
            "NTS RIO JANEIRO": "NTS RIO DE JANEIRO",
            "RIO": "NTS RIO DE JANEIRO",

            "NTS SAO PAULO": "NTS SAO PAULO",
            "NTS SP": "NTS SAO PAULO",
            "SAO PAULO": "NTS SAO PAULO",
            "SP": "NTS SAO PAULO",

            "NTS BELEM": "NTS BELEM",
            "NTS BELÉM": "NTS BELEM",
            "BELEM": "NTS BELEM",
        }

        return mapping.get(raw, raw)

    def build(self, estoque_df, vendas_df):

        hoje = datetime.today().date()

        estoque = estoque_df.copy()
        vendas = vendas_df.copy()

        estoque["codigo_produto"] = estoque["Codigo_Supra"].astype(str).str.strip()
        vendas["codigo_produto"] = vendas["prod_codigo"].astype(str).str.strip()

        estoque["empresa_key"] = estoque["Empresa"].apply(self.normalize_company)
        vendas["empresa_key"] = vendas["Empresa"].apply(self.normalize_company)

        estoque["Quantidade_Estoque"] = pd.to_numeric(
            estoque["Quantidade_Estoque"],
            errors="coerce"
        ).fillna(0)

        estoque["preco_custo"] = pd.to_numeric(
            estoque["preco_custo"],
            errors="coerce"
        ).fillna(0)

        vendas["Quantidade"] = pd.to_numeric(
            vendas["Quantidade"],
            errors="coerce"
        ).fillna(0)

        vendas["Valor_total_Unitario"] = pd.to_numeric(
            vendas["Valor_total_Unitario"],
            errors="coerce"
        ).fillna(0)

        vendas["Data"] = pd.to_datetime(
            vendas["Data"],
            errors="coerce"
        )

        data_limite_30 = pd.Timestamp(hoje) - pd.Timedelta(days=30)
        data_limite_90 = pd.Timestamp(hoje) - pd.Timedelta(days=90)

        vendas_30 = vendas[vendas["Data"] >= data_limite_30]
        vendas_90 = vendas[vendas["Data"] >= data_limite_90]

        vendas_30_agg = (
            vendas_30
            .groupby(["codigo_produto", "empresa_key"], dropna=False)
            .agg(
                qtd_vendida_30d=("Quantidade", "sum"),
                faturamento_30d=("Valor_total_Unitario", "sum")
            )
            .reset_index()
        )

        vendas_90_agg = (
            vendas_90
            .groupby(["codigo_produto", "empresa_key"], dropna=False)
            .agg(
                qtd_vendida_90d=("Quantidade", "sum"),
                faturamento_90d=("Valor_total_Unitario", "sum"),
                ultima_venda=("Data", "max")
            )
            .reset_index()
        )

        base = estoque.merge(
            vendas_30_agg,
            on=["codigo_produto", "empresa_key"],
            how="left"
        )

        base = base.merge(
            vendas_90_agg,
            on=["codigo_produto", "empresa_key"],
            how="left"
        )

        base["qtd_vendida_30d"] = base["qtd_vendida_30d"].fillna(0)
        base["faturamento_30d"] = base["faturamento_30d"].fillna(0)
        base["qtd_vendida_90d"] = base["qtd_vendida_90d"].fillna(0)
        base["faturamento_90d"] = base["faturamento_90d"].fillna(0)

        base["valor_estoque"] = (
            base["Quantidade_Estoque"] * base["preco_custo"]
        )

        base["media_venda_mensal"] = base["qtd_vendida_90d"] / 3

        base["cobertura_estoque"] = base.apply(
            lambda row: (
                row["Quantidade_Estoque"] / row["media_venda_mensal"]
                if row["media_venda_mensal"] > 0
                else None
            ),
            axis=1
        )

        base["dias_sem_venda"] = base["ultima_venda"].apply(
            lambda value: (
                (pd.Timestamp(hoje) - value).days
                if pd.notnull(value)
                else None
            )
        )

        def classify_risk(row):

            curva = str(row.get("Curva_ABCDE", "")).upper().strip()
            estoque_atual = row["Quantidade_Estoque"]
            qtd_90 = row["qtd_vendida_90d"]
            cobertura = row["cobertura_estoque"]
            dias_sem_venda = row["dias_sem_venda"]

            if estoque_atual <= 0 and qtd_90 > 0:
                return "ruptura"

            if curva == "A" and estoque_atual <= 0:
                return "curva_a_critico"

            if estoque_atual > 0 and dias_sem_venda is not None and dias_sem_venda >= 60:
                return "sem_giro"

            if cobertura is not None and cobertura >= 6:
                return "excesso"

            return "normal"

        base["risk_type"] = base.apply(classify_risk, axis=1)

        def classify_status(risk_type):

            if risk_type in ["ruptura", "curva_a_critico"]:
                return "critical"

            if risk_type in ["sem_giro", "excesso"]:
                return "attention"

            return "healthy"

        base["status"] = base["risk_type"].apply(classify_status)

        return base