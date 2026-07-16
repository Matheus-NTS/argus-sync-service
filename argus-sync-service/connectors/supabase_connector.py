import os

from dotenv import load_dotenv
from supabase import create_client


class SupabaseConnector:

    def __init__(self):

        load_dotenv("config/.env")

        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SECRET_KEY")

        if not self.url:
            raise ValueError(
                "SUPABASE_URL não foi configurada."
            )

        if not self.key:
            raise ValueError(
                "SUPABASE_SECRET_KEY não foi configurada."
            )

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

    def insert_batches(
        self,
        table_name,
        data,
        batch_size=500
    ):

        if not data:
            return []

        responses = []

        for start in range(
            0,
            len(data),
            batch_size
        ):

            batch = data[
                start:start + batch_size
            ]

            response = self.insert(
                table_name,
                batch
            )

            responses.append(response)

        return responses

    def upsert(
        self,
        table_name,
        data,
        conflict_columns
    ):

        return (
            self.client
            .table(table_name)
            .upsert(
                data,
                on_conflict=conflict_columns
            )
            .execute()
        )

    def delete_where(
        self,
        table_name,
        filters
    ):

        if not filters:
            raise ValueError(
                "delete_where exige ao menos um filtro."
            )

        query = (
            self.client
            .table(table_name)
            .delete()
        )

        for column, value in filters.items():
            query = query.eq(
                column,
                value
            )

        return query.execute()

    def delete_all(self, table_name):

        return (
            self.client
            .table(table_name)
            .delete()
            .gte("id", 0)
            .execute()
        )

    def replace_snapshot(
        self,
        table_name,
        filters,
        data
    ):

        self.delete_where(
            table_name,
            filters
        )

        if not data:
            return None

        return self.insert(
            table_name,
            data
        )

    def replace_snapshot_batches(
        self,
        table_name,
        filters,
        data,
        batch_size=500
    ):

        self.delete_where(
            table_name,
            filters
        )

        if not data:
            return []

        return self.insert_batches(
            table_name=table_name,
            data=data,
            batch_size=batch_size
        )