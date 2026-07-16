import re
import unicodedata

import pandas as pd
from sqlalchemy import text


class ProdutoExtractor:

    def __init__(self, connector):
        self.connector = connector

    @staticmethod
    def _normalize_text(value) -> str:
        if pd.isna(value):
            return ""

        text_value = str(value).strip().upper()

        text_value = unicodedata.normalize("NFKD", text_value)
        text_value = "".join(
            char for char in text_value
            if not unicodedata.combining(char)
        )

        return " ".join(text_value.split())

    @classmethod
    def _is_valid_product_name(cls, value) -> bool:
        normalized = cls._normalize_text(value)

        if not normalized:
            return False

        # Exclui registros administrativos ou de teste.
        blocked_terms = [
            "TREINAMENTO"
        ]

        if any(term in normalized for term in blocked_terms):
            return False

        # O nome precisa possuir pelo menos uma letra ou número.
        # Assim são eliminados ".", "-", ":", ";", "," e símbolos isolados.
        if not re.search(r"[A-Z0-9]", normalized):
            return False

        return True

    def extract(self):

        query = text("""
            SELECT *
            FROM dbo.agrc_produto_lucas
            WHERE tipo = 'Produto'
        """)

        df = pd.read_sql(query, self.connector.engine)

        if "Descricao" not in df.columns:
            raise KeyError(
                "A coluna 'Descricao' não foi encontrada em agrc_produto_lucas."
            )

        total_before = len(df)

        df = df[
            df["Descricao"].apply(self._is_valid_product_name)
        ].copy()

        total_after = len(df)

        print(
            f"  Produtos extraídos: {total_before} registros | "
            f"válidos para estoque: {total_after} | "
            f"descartados: {total_before - total_after}"
        )

        return df