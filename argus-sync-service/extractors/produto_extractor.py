import pandas as pd
from sqlalchemy import text


class ProdutoExtractor:

    def __init__(self, connector):
        self.connector = connector

    def extract(self):

        query = text("""
            SELECT *
            FROM dbo.agrc_produto_lucas
        """)

        df = pd.read_sql(query, self.connector.engine)

        return df