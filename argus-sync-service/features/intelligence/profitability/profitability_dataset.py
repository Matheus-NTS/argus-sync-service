import re
import unicodedata

import pandas as pd


class ProfitabilityDataset:

    OFFICIAL_COMPANIES = {
        "NTS RIO",
        "NTS SAO PAULO",
        "NTS BELEM",
    }

    @staticmethod
    def normalize_text(value):

        if pd.isna(value):
            return None

        cleaned = " ".join(str(value).strip().split())

        return cleaned or None

    @staticmethod
    def normalize_text_key(value):

        if pd.isna(value):
            return ""

        raw = str(value).strip().upper()

        raw = (
            unicodedata
            .normalize("NFD", raw)
            .encode("ascii", "ignore")
            .decode("utf-8")
        )

        return " ".join(raw.split())

    @staticmethod
    def normalize_code(value):

        if pd.isna(value):
            return None

        raw = str(value).strip()

        if not raw:
            return None

        if re.fullmatch(r"\d+\.0", raw):
            raw = raw[:-2]

        if raw.isdigit():
            return raw.zfill(6)

        return raw.upper()

    @staticmethod
    def normalize_company(value):

        if pd.isna(value):
            return None

        raw = str(value).strip().upper()

        raw = (
            unicodedata
            .normalize("NFD", raw)
            .encode("ascii", "ignore")
            .decode("utf-8")
        )

        raw = " ".join(raw.split())

        mapping = {
            "NTS RIO": "NTS RIO",
            "NTS RIO DE JANEIRO": "NTS RIO",
            "NTS RIO JANEIRO": "NTS RIO",
            "RIO": "NTS RIO",

            "NTS SAO PAULO": "NTS SAO PAULO",
            "NTS SP": "NTS SAO PAULO",
            "SAO PAULO": "NTS SAO PAULO",
            "SP": "NTS SAO PAULO",

            "NTS BELEM": "NTS BELEM",
            "BELEM": "NTS BELEM",
        }

        return mapping.get(raw, raw)

    def _validate_columns(self, vendas_df, produtos_df):

        vendas_required = [
            "Data",
            "Vendedor",
            "numero_pedido",
            "prod_codigo",
            "produto",
            "Classificacao",
            "Quantidade",
            "valor_unitario",
            "Valor_total_Unitario",
            "Empresa",
            "codigo_cliente",
            "Cliente",
        ]

        produtos_required = [
            "codigo_produto",
            "empresa_key",
            "produto_cadastro",
            "codigo_fabricante",
            "curva_abcde",
            "preco_custo",
        ]

        missing_sales = [
            column
            for column in vendas_required
            if column not in vendas_df.columns
        ]

        missing_products = [
            column
            for column in produtos_required
            if column not in produtos_df.columns
        ]

        if missing_sales:
            raise KeyError(
                "Colunas obrigatórias ausentes em pedidos: "
                + ", ".join(missing_sales)
            )

        if missing_products:
            raise KeyError(
                "Colunas obrigatórias ausentes em produtos tratados: "
                + ", ".join(missing_products)
            )

    def _is_product_out_of_scope(self, product_name):

        key = self.normalize_text_key(product_name)

        if not key:
            return True

        # Nome composto somente por símbolos.
        if not re.search(r"[A-Z0-9]", key):
            return True

        excluded_terms = [
            "TREINAMENTO",
            "NTS ACADEMY",
            "MAO DE OBRA",
            "SERVICO DE MAO DE OBRA",
            "TESTE DE BICO",
            "TESTE BICO",
        ]

        return any(
            term in key
            for term in excluded_terms
        )

    @staticmethod
    def _classify_financial_anomaly(row):

        if not row["custo_valido"]:
            return False

        margem = row["margem_percentual"]
        preco_venda_medio = row["preco_venda_medio"]
        preco_custo = row["preco_custo"]

        # Prejuízo superior ao próprio valor faturado.
        if (
            margem is not None
            and not pd.isna(margem)
            and margem < -100
        ):
            return True

        # Preço médio inferior a 10% do custo unitário atual.
        if (
            preco_custo is not None
            and not pd.isna(preco_custo)
            and preco_custo > 0
            and preco_venda_medio is not None
            and not pd.isna(preco_venda_medio)
            and preco_venda_medio < (preco_custo * 0.10)
        ):
            return True

        return False

    @staticmethod
    def _classify_profitability(row):

        if not row["empresa_oficial"]:
            return "empresa_fora_escopo"

        if row["produto_fora_escopo"]:
            return "produto_fora_escopo"

        if not row["custo_valido"]:
            return "sem_custo_valido"

        if row["dado_suspeito"]:
            return "dado_suspeito"

        margem = row["margem_percentual"]

        if margem is None or pd.isna(margem):
            return "sem_margem"

        if margem < 0:
            return "prejuizo"

        if margem < 5:
            return "critico"

        if margem < 10:
            return "margem_baixa"

        if margem < 20:
            return "monitoramento"

        if margem < 30:
            return "saudavel"

        if margem < 40:
            return "alta_rentabilidade"

        return "excelente"

    @staticmethod
    def _classify_analysis_status(row):

        if not row["empresa_oficial"]:
            return "empresa_fora_escopo"

        if row["produto_fora_escopo"]:
            return "produto_fora_escopo"

        if not row["custo_valido"]:
            return "sem_custo_valido"

        if row["dado_suspeito"]:
            return "dado_suspeito"

        return "analisavel"

    def build(self, vendas_df, produtos_df):

        self._validate_columns(
            vendas_df,
            produtos_df
        )

        vendas = vendas_df.copy()
        produtos = produtos_df.copy()

        vendas["codigo_produto"] = (
            vendas["prod_codigo"]
            .apply(self.normalize_code)
        )

        vendas["empresa_key"] = (
            vendas["Empresa"]
            .apply(self.normalize_company)
        )

        vendas["data_venda"] = pd.to_datetime(
            vendas["Data"],
            errors="coerce"
        )

        vendas["quantidade"] = pd.to_numeric(
            vendas["Quantidade"],
            errors="coerce"
        ).fillna(0)

        vendas["preco_venda_unitario"] = pd.to_numeric(
            vendas["valor_unitario"],
            errors="coerce"
        ).fillna(0)

        vendas["faturamento"] = pd.to_numeric(
            vendas["Valor_total_Unitario"],
            errors="coerce"
        ).fillna(0)

        vendas["vendedor"] = (
            vendas["Vendedor"]
            .apply(self.normalize_text)
        )

        vendas["cliente"] = (
            vendas["Cliente"]
            .apply(self.normalize_text)
        )

        vendas["produto_venda"] = (
            vendas["produto"]
            .apply(self.normalize_text)
        )

        vendas["categoria"] = (
            vendas["Classificacao"]
            .apply(self.normalize_text)
        )

        vendas["codigo_cliente_normalizado"] = (
            vendas["codigo_cliente"]
            .apply(self.normalize_text)
        )

        base = vendas.merge(
            produtos,
            on=["codigo_produto", "empresa_key"],
            how="left",
            validate="many_to_one",
            indicator=True
        )

        base["produto"] = (
            base["produto_venda"]
            .fillna(base["produto_cadastro"])
        )

        base["preco_custo"] = pd.to_numeric(
            base["preco_custo"],
            errors="coerce"
        )

        def classify_cost_status(row):

            if row["_merge"] == "left_only":
                return "produto_nao_encontrado"

            if pd.isna(row["preco_custo"]):
                return "custo_ausente"

            if row["preco_custo"] <= 0:
                return "custo_zerado"

            if row["quantidade"] <= 0:
                return "quantidade_invalida"

            if row["faturamento"] <= 0:
                return "faturamento_invalido"

            return "valido"

        base["status_custo"] = base.apply(
            classify_cost_status,
            axis=1
        )

        base["custo_valido"] = (
            base["status_custo"] == "valido"
        )

        base["empresa_oficial"] = (
            base["empresa_key"]
            .isin(self.OFFICIAL_COMPANIES)
        )

        base["produto_fora_escopo"] = (
            base["produto"]
            .apply(self._is_product_out_of_scope)
        )

        base["preco_venda_medio"] = base.apply(
            lambda row: (
                row["faturamento"] / row["quantidade"]
                if row["quantidade"] > 0
                else None
            ),
            axis=1
        )

        base["custo_total"] = (
            base["preco_custo"]
            * base["quantidade"]
        )

        base.loc[
            ~base["custo_valido"],
            "custo_total"
        ] = None

        base["lucro_bruto"] = (
            base["faturamento"]
            - base["custo_total"]
        )

        base["margem_percentual"] = base.apply(
            lambda row: (
                (row["lucro_bruto"] / row["faturamento"]) * 100
                if (
                    row["custo_valido"]
                    and row["faturamento"] != 0
                )
                else None
            ),
            axis=1
        )

        base["markup_percentual"] = base.apply(
            lambda row: (
                (row["lucro_bruto"] / row["custo_total"]) * 100
                if (
                    row["custo_valido"]
                    and row["custo_total"] != 0
                )
                else None
            ),
            axis=1
        )

        base["dado_suspeito"] = base.apply(
            self._classify_financial_anomaly,
            axis=1
        )

        base["status_analise"] = base.apply(
            self._classify_analysis_status,
            axis=1
        )

        base["elegivel_kpi"] = (
            base["status_analise"] == "analisavel"
        )

        base["status_rentabilidade"] = base.apply(
            self._classify_profitability,
            axis=1
        )

        # Os valores originais permanecem na base.
        # Estas colunas são as que devem compor os KPIs oficiais.
        base["faturamento_analisavel"] = base[
            "faturamento"
        ].where(base["elegivel_kpi"])

        base["custo_analisavel"] = base[
            "custo_total"
        ].where(base["elegivel_kpi"])

        base["lucro_analisavel"] = base[
            "lucro_bruto"
        ].where(base["elegivel_kpi"])

        base["ano"] = base["data_venda"].dt.year
        base["mes"] = base["data_venda"].dt.month

        base["ano_mes"] = (
            base["data_venda"]
            .dt.to_period("M")
            .astype(str)
        )

        base = base.drop(columns=["_merge"])

        return base[
            [
                "data_venda",
                "ano",
                "mes",
                "ano_mes",
                "numero_pedido",
                "empresa_key",
                "empresa_oficial",
                "vendedor",
                "codigo_cliente_normalizado",
                "cliente",
                "codigo_produto",
                "codigo_fabricante",
                "produto",
                "produto_fora_escopo",
                "categoria",
                "curva_abcde",
                "quantidade",
                "preco_venda_unitario",
                "preco_venda_medio",
                "preco_custo",
                "faturamento",
                "custo_total",
                "lucro_bruto",
                "margem_percentual",
                "markup_percentual",
                "status_custo",
                "custo_valido",
                "dado_suspeito",
                "status_analise",
                "elegivel_kpi",
                "faturamento_analisavel",
                "custo_analisavel",
                "lucro_analisavel",
                "status_rentabilidade",
            ]
        ].copy()