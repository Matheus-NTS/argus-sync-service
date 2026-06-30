import pandas as pd
from sqlalchemy import text


class MetaExtractor:

    def __init__(self, connector):
        self.connector = connector

    def extract(self):
        query = text("""
            SELECT *
            FROM dbo.agrc_meta_vendedor
        """)

        df = pd.read_sql(query, self.connector.engine)

        return df