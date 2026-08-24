import json
from pathlib import Path

import pandas as pd
from sqlalchemy import text


class ProductMetadataCache:
    """
    Cache persistente de metadados de produto.

    O Sync normal apenas le o cache local.
    Consultas historicas pesadas nao fazem parte
    do ciclo recorrente do Stock Pipeline.
    """

    def __init__(
        self,
        sql_connector,
        cache_path=None,
    ):
        self.sql_connector = sql_connector

        base_dir = Path(__file__).resolve().parents[1]

        self.cache_path = Path(
            cache_path
            or base_dir
            / ".runtime"
            / "product_metadata.json"
        )

    def build(self):
        """
        Constroi o cache completo.

        Operacao deliberadamente separada do Sync normal.
        """
        query = text("""
            WITH base AS (
                SELECT DISTINCT
                    LTRIM(RTRIM(Codigo_Supra))
                        AS Codigo_Supra,
                    NULLIF(
                        LTRIM(
                            RTRIM(Codigo_Fabricante)
                        ),
                        ''
                    ) AS Codigo_Fabricante
                FROM dbo.agrc_produto_lucas
                WHERE tipo = 'Produto'
                  AND Codigo_Supra IS NOT NULL
                  AND LTRIM(RTRIM(Codigo_Supra)) <> ''
            ),
            cons AS (
                SELECT
                    LTRIM(RTRIM(Codigo_Supra))
                        AS Codigo_Supra,
                    NULLIF(
                        LTRIM(RTRIM(Fabricante)),
                        ''
                    ) AS Fabricante,
                    NULLIF(
                        LTRIM(
                            RTRIM(
                                Classificacao_Produto
                            )
                        ),
                        ''
                    ) AS Classificacao_Produto
                FROM dbo.agrc_cons_prod_lucas
            ),
            faltantes AS (
                SELECT b.Codigo_Supra
                FROM base b
                LEFT JOIN cons c
                    ON c.Codigo_Supra =
                       b.Codigo_Supra
                WHERE c.Codigo_Supra IS NULL
            ),
            sgr AS (
                SELECT
                    LTRIM(
                        RTRIM(s.Codigo_Produto)
                    ) AS Codigo_Supra,
                    MAX(
                        NULLIF(
                            LTRIM(
                                RTRIM(s.Fabricante)
                            ),
                            ''
                        )
                    ) AS Fabricante,
                    MAX(
                        NULLIF(
                            LTRIM(
                                RTRIM(
                                    s.Classificacao_Produto
                                )
                            ),
                            ''
                        )
                    ) AS Classificacao_Produto
                FROM dbo.sgr_pedidos s
                INNER JOIN faltantes f
                    ON f.Codigo_Supra =
                       LTRIM(
                           RTRIM(
                               s.Codigo_Produto
                           )
                       )
                GROUP BY
                    LTRIM(
                        RTRIM(
                            s.Codigo_Produto
                        )
                    )
            )
            SELECT
                b.Codigo_Supra,
                b.Codigo_Fabricante,
                COALESCE(
                    c.Fabricante,
                    s.Fabricante
                ) AS Fabricante,
                COALESCE(
                    c.Classificacao_Produto,
                    s.Classificacao_Produto
                ) AS Classificacao_Produto
            FROM base b
            LEFT JOIN cons c
                ON c.Codigo_Supra =
                   b.Codigo_Supra
            LEFT JOIN sgr s
                ON s.Codigo_Supra =
                   b.Codigo_Supra
        """)

        df = pd.read_sql(
            query,
            self.sql_connector.engine,
        )

        metadata = {}

        def clean_value(value):
            if pd.isna(value):
                return None

            text_value = str(value).strip()

            return text_value or None

        for row in df.to_dict("records"):
            codigo = clean_value(
                row.get("Codigo_Supra")
            )

            if not codigo:
                continue

            metadata[codigo] = {
                "Codigo_Fabricante": clean_value(
                    row.get("Codigo_Fabricante")
                ),
                "Fabricante": clean_value(
                    row.get("Fabricante")
                ),
                "Classificacao_Produto": clean_value(
                    row.get(
                        "Classificacao_Produto"
                    )
                ),
            }

        self.cache_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = self.cache_path.with_suffix(
            ".tmp"
        )

        temp_path.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        temp_path.replace(
            self.cache_path
        )

        return metadata

    def load(self):
        if not self.cache_path.exists():
            raise FileNotFoundError(
                "Cache de metadados de produto "
                "ainda nao foi criado."
            )

        return json.loads(
            self.cache_path.read_text(
                encoding="utf-8"
            )
        )

    def enrich(self, products_df):
        """
        Enriquece um DataFrame sem rede.

        Preserva Codigo_Fabricante vindo
        diretamente da base principal.
        """
        df = products_df.copy()

        metadata = self.load()

        codigo = (
            df["Codigo_Supra"]
            .astype(str)
            .str.strip()
        )

        for field in (
            "Fabricante",
            "Classificacao_Produto",
        ):
            df[field] = codigo.map(
                lambda value: (
                    metadata
                    .get(value, {})
                    .get(field)
                )
            )

        return df
