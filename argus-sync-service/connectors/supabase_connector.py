import os

from dotenv import load_dotenv
from supabase import create_client


class SupabaseConnector:

    def __init__(self):
        load_dotenv(dotenv_path="config/.env")

        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SECRET_KEY")

        self.client = create_client(
            self.url,
            self.key
        )

    def insert(self, table_name, data):
        response = self.client.table(table_name).insert(data).execute()
        return response