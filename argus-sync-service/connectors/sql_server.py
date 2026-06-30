import os
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


class SQLServerConnector:
    def __init__(self):
        load_dotenv(dotenv_path="config/.env")

        self.server = os.getenv("SQL_SERVER")
        self.port = os.getenv("SQL_PORT")
        self.database = os.getenv("SQL_DATABASE")
        self.user = os.getenv("SQL_USER")
        self.password = os.getenv("SQL_PASSWORD")
        self.driver = os.getenv("SQL_DRIVER")

        self.engine = self._create_engine()

    def _create_engine(self):
        driver_encoded = quote_plus(self.driver)

        connection_string = (
    f"mssql+pyodbc://{self.user}:{self.password}"
    f"@{self.server}:{self.port}/{self.database}"
    f"?driver={driver_encoded}"
    f"&TrustServerCertificate=yes"
)

        return create_engine(connection_string)

    def test_connection(self):
        query = text("SELECT TOP 10 * FROM dbo.agrc_pedido_lucas")
        df = pd.read_sql(query, self.engine)
        return df