import pandas as pd
from sqlalchemy import text


class PedidoExtractor:

    def __init__(self, connector):
        self.connector = connector

    def extract(self):

        query_pedidos = text("""
            SELECT *
            FROM dbo.agrc_pedido_lucas
        """)

        query_pedidos_ants = text("""
            SELECT *
            FROM dbo.agrc_pedido_ANTS_lucas
        """)

        df_pedidos = pd.read_sql(
            query_pedidos,
            self.connector.engine
        )

        df_pedidos_ants = pd.read_sql(
            query_pedidos_ants,
            self.connector.engine
        )

        # A view histórica usa "Situacao" e a atual usa "situacao".
        # Padronizamos antes de juntar as bases.
        if (
            "Situacao" in df_pedidos_ants.columns
            and "situacao" not in df_pedidos_ants.columns
        ):
            df_pedidos_ants = df_pedidos_ants.rename(
                columns={"Situacao": "situacao"}
            )

        # Mantém todas as colunas da view atual.
        # As colunas inexistentes na ANTS ficam nulas apenas
        # nos registros históricos.
        df = pd.concat(
            [df_pedidos, df_pedidos_ants],
            ignore_index=True,
            sort=False
        )

        return df