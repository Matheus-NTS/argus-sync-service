import os

from dotenv import load_dotenv
from supabase import create_client


class SupabaseConnector:

    def __init__(self):

        load_dotenv("config/.env")

        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SECRET_KEY")

        self.client = create_client(
            self.url,
            self.key
        )

    def insert(self, table_name, data):

        return (
            self.client
            .table(table_name)
            .insert(data)
            .execute()
        )

    def upsert(self, table_name, data, conflict_columns):

        return (
            self.client
            .table(table_name)
            .upsert(
                data,
                on_conflict=conflict_columns
            )
            .execute()
        )

    def delete_where(self, table_name, filters):

        query = self.client.table(table_name).delete()

        for column, value in filters.items():
            query = query.eq(column, value)

        return query.execute()