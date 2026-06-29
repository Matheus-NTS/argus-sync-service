import os
from dotenv import load_dotenv


class SQLServerConnector:
    def __init__(self):
        load_dotenv(dotenv_path="config/.env")

        self.server = os.getenv("SQL_SERVER")
        self.port = os.getenv("SQL_PORT")
        self.database = os.getenv("SQL_DATABASE")
        self.user = os.getenv("SQL_USER")
        self.password = os.getenv("SQL_PASSWORD")
        self.driver = os.getenv("SQL_DRIVER")

    def show_config(self):
        print("SQL Server configuration loaded:")
        print(f"Server: {self.server}")
        print(f"Port: {self.port}")
        print(f"Database: {self.database}")
        print(f"User: {self.user}")
        print(f"Driver: {self.driver}")
        print("Password: ********")