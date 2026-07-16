import re
import unicodedata

import pandas as pd


class ProdutoTransformer:

    @staticmethod
    def normalize_text(value):

        if pd.isna(value):
            return None

        cleaned = " ".join(str(value).strip().split())

        return cleaned or None

    @staticmethod
    def normalize_code(value):

        if pd.isna(value):
            return None

        raw = str(value).strip()

        if not raw:
            return None

        # Corrige códigos que eventualmente chegam como 693.0.
        if re.fullmatch(r"\d+\.0", raw):
            raw = raw[:-2]

        # Os códigos Supra numéricos usam seis posições.
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

    def prepare(self, produtos_df):

        required_columns = [
            "Codigo_Supra",
            "Codigo_Fabricante",
            "Descricao",
            "preco_custo",
            "Empresa",
            "Curva_ABCDE",
            "Tipo",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in produtos_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes em produtos: "
                + ", ".join(missing_columns)
            )

        produtos = produtos_df.copy()

        # Regra oficial: somente registros cujo Tipo seja Produto.
        tipo_normalizado = (
            produtos["Tipo"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        produtos = produtos[
            tipo_normalizado == "PRODUTO"
        ].copy()

        produtos["codigo_produto"] = (
            produtos["Codigo_Supra"]
            .apply(self.normalize_code)
        )

        produtos["empresa_key"] = (
            produtos["Empresa"]
            .apply(self.normalize_company)
        )

        produtos["produto_cadastro"] = (
            produtos["Descricao"]
            .apply(self.normalize_text)
        )

        produtos["codigo_fabricante"] = (
            produtos["Codigo_Fabricante"]
            .apply(self.normalize_text)
        )

        produtos["curva_abcde"] = (
            produtos["Curva_ABCDE"]
            .apply(self.normalize_text)
        )

        produtos["preco_custo"] = pd.to_numeric(
            produtos["preco_custo"],
            errors="coerce"
        )

        produtos = produtos[
            produtos["codigo_produto"].notna()
            & produtos["empresa_key"].notna()
        ].copy()

        duplicate_mask = produtos.duplicated(
            subset=["codigo_produto", "empresa_key"],
            keep=False
        )

        duplicate_count = int(duplicate_mask.sum())

        if duplicate_count > 0:
            print(
                "  Aviso Rentabilidade: "
                f"{duplicate_count} posições duplicadas em "
                "código + empresa. Mantendo a última ocorrência."
            )

            produtos = produtos.drop_duplicates(
                subset=["codigo_produto", "empresa_key"],
                keep="last"
            )

        return produtos[
            [
                "codigo_produto",
                "empresa_key",
                "produto_cadastro",
                "codigo_fabricante",
                "curva_abcde",
                "preco_custo",
            ]
        ].copy()