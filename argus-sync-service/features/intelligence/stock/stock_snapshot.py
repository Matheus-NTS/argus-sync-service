from datetime import datetime

import math
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

    def _coverage_factor(self, curva):

        curva = str(curva or "").strip().upper()

        mapping = {
            "A": 2.5,
            "B": 2.0,
            "C": 1.5,
            "D": 1.0,
            "E": 0.5
        }

        return mapping.get(curva, 1.0)

    def _classify_replenishment(self, estoque_atual, media_6m, estoque_ideal, ponto_pedido):

        if media_6m <= 0:
            return "sem_demanda"

        if estoque_atual <= ponto_pedido:
            return "comprar_agora"

        if estoque_atual <= estoque_ideal:
            return "atencao"

        if estoque_atual > (estoque_ideal * 2):
            return "excesso"

        return "saudavel"

    def _replenishment_action(self, status):

        mapping = {
            "comprar_agora": "Comprar agora",
            "atencao": "Planejar reposição",
            "saudavel": "Sem ação imediata",
            "excesso": "Revisar excesso / capital parado",
            "sem_demanda": "Sem demanda recente"
        }

        return mapping.get(status, "Sem ação")

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
        data_limite_180 = pd.Timestamp(hoje) - pd.Timedelta(days=180)

        vendas_30 = vendas[vendas["Data"] >= data_limite_30]
        vendas_90 = vendas[vendas["Data"] >= data_limite_90]
        vendas_180 = vendas[vendas["Data"] >= data_limite_180]

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

        vendas_180_agg = (
            vendas_180
            .groupby(["codigo_produto", "empresa_key"], dropna=False)
            .agg(
                qtd_vendida_180d=("Quantidade", "sum"),
                faturamento_180d=("Valor_total_Unitario", "sum")
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

        base = base.merge(
            vendas_180_agg,
            on=["codigo_produto", "empresa_key"],
            how="left"
        )

        for col in [
            "qtd_vendida_30d",
            "faturamento_30d",
            "qtd_vendida_90d",
            "faturamento_90d",
            "qtd_vendida_180d",
            "faturamento_180d"
        ]:
            base[col] = base[col].fillna(0)

        base["valor_estoque"] = (
            base["Quantidade_Estoque"] * base["preco_custo"]
        )

        base["media_venda_mensal"] = base["qtd_vendida_90d"] / 3
        base["media_venda_6m"] = base["qtd_vendida_180d"] / 6

        base["cobertura_estoque"] = base.apply(
            lambda row: (
                row["Quantidade_Estoque"] / row["media_venda_mensal"]
                if row["media_venda_mensal"] > 0
                else None
            ),
            axis=1
        )

        base["dias_para_esgotar"] = base.apply(
            lambda row: (
                round((row["Quantidade_Estoque"] / row["media_venda_6m"]) * 30, 0)
                if row["media_venda_6m"] > 0
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

        base["fator_cobertura"] = base["Curva_ABCDE"].apply(self._coverage_factor)

        base["estoque_ideal"] = (
            base["media_venda_6m"] * base["fator_cobertura"]
        )

        base["ponto_pedido"] = base["media_venda_6m"]

        base["sugestao_compra"] = base.apply(
            lambda row: max(
                math.ceil(row["estoque_ideal"] - row["Quantidade_Estoque"]),
                0
            ),
            axis=1
        )

        base["replenishment_status"] = base.apply(
            lambda row: self._classify_replenishment(
                estoque_atual=row["Quantidade_Estoque"],
                media_6m=row["media_venda_6m"],
                estoque_ideal=row["estoque_ideal"],
                ponto_pedido=row["ponto_pedido"]
            ),
            axis=1
        )

        base["replenishment_action"] = base["replenishment_status"].apply(
            self._replenishment_action
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