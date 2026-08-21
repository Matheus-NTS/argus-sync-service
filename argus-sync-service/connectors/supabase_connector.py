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

    def select_rows(
        self,
        table_name,
        columns="*",
        filters=None,
        lt_filters=None,
        lte_filters=None,
        gt_filters=None,
        gte_filters=None,
        order_by=None,
        descending=False,
        limit=None
    ):

        query = (
            self.client
            .table(table_name)
            .select(columns)
        )

        for column, value in (filters or {}).items():
            query = query.eq(
                column,
                value
            )

        for column, value in (lt_filters or {}).items():
            query = query.lt(
                column,
                value
            )

        for column, value in (lte_filters or {}).items():
            query = query.lte(
                column,
                value
            )

        for column, value in (gt_filters or {}).items():
            query = query.gt(
                column,
                value
            )

        for column, value in (gte_filters or {}).items():
            query = query.gte(
                column,
                value
            )

        if order_by:
            query = query.order(
                order_by,
                desc=descending
            )

        if limit is not None:
            query = query.limit(
                limit
            )

        response = query.execute()

        return response.data or []

    def select_rows_paginated(
        self,
        table_name,
        columns="*",
        filters=None,
        order_by=None,
        descending=False,
        page_size=1000
    ):

        if page_size <= 0:
            raise ValueError(
                "page_size deve ser maior que zero."
            )

        rows = []
        start = 0

        while True:

            query = (
                self.client
                .table(table_name)
                .select(columns)
            )

            for column, value in (
                filters or {}
            ).items():
                query = query.eq(
                    column,
                    value
                )

            if order_by:
                query = query.order(
                    order_by,
                    desc=descending
                )

            end = (
                start
                + page_size
                - 1
            )

            response = (
                query
                .range(
                    start,
                    end
                )
                .execute()
            )

            page = response.data or []

            rows.extend(page)

            if len(page) < page_size:
                break

            start += page_size

        return rows

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

        if batch_size <= 0:
            raise ValueError(
                "batch_size deve ser maior que zero."
            )

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

    def upsert_batches(
        self,
        table_name,
        data,
        conflict_columns,
        batch_size=500
    ):

        if not data:
            return []

        if batch_size <= 0:
            raise ValueError(
                "batch_size deve ser maior que zero."
            )

        responses = []

        for start in range(
            0,
            len(data),
            batch_size
        ):
            batch = data[
                start:start + batch_size
            ]

            response = self.upsert(
                table_name,
                batch,
                conflict_columns
            )

            responses.append(response)

        return responses

    def update_rows(
        self,
        table_name,
        values,
        filters,
    ):
        """
        Atualiza linhas usando filtros de igualdade.

        Nenhum update sem filtro e permitido.
        """
        if not values:
            raise ValueError(
                "update_rows exige values."
            )

        if not filters:
            raise ValueError(
                "update_rows exige ao menos um filtro."
            )

        from postgrest.types import ReturnMethod

        query = (
            self.client
            .table(table_name)
            .update(
                values,
                returning=ReturnMethod.minimal,
            )
        )

        for column, value in filters.items():
            query = query.eq(
                column,
                value,
            )

        return query.execute()

    def delete_ids_batches(
        self,
        table_name,
        ids,
        id_column="id",
        batch_size=250
    ):

        if not ids:
            return []

        if batch_size <= 0:
            raise ValueError(
                "batch_size deve ser maior que zero."
            )

        responses = []

        for start in range(
            0,
            len(ids),
            batch_size
        ):
            batch = ids[
                start:start + batch_size
            ]

            response = (
                self.client
                .table(table_name)
                .delete()
                .in_(
                    id_column,
                    batch
                )
                .execute()
            )

            responses.append(response)

        return responses

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

    def delete_where_batches(
        self,
        table_name,
        filters,
        batch_size=250,
        id_column="id"
    ):

        if not filters:
            raise ValueError(
                "delete_where_batches exige ao menos um filtro."
            )

        if batch_size <= 0:
            raise ValueError(
                "batch_size deve ser maior que zero."
            )

        responses = []
        deleted_rows = 0

        while True:

            select_query = (
                self.client
                .table(table_name)
                .select(id_column)
            )

            for column, value in filters.items():
                select_query = select_query.eq(
                    column,
                    value
                )

            selection = (
                select_query
                .order(
                    id_column,
                    desc=False
                )
                .limit(batch_size)
                .execute()
            )

            rows = selection.data or []

            if not rows:
                break

            ids = [
                row[id_column]
                for row in rows
                if row.get(id_column) is not None
            ]

            if not ids:
                raise RuntimeError(
                    f"Não foi possível localizar valores válidos "
                    f"na coluna {id_column!r} de {table_name!r}."
                )

            response = (
                self.client
                .table(table_name)
                .delete()
                .in_(id_column, ids)
                .execute()
            )

            responses.append(response)
            deleted_rows += len(ids)

            print(
                f"  Exclusão em lotes: {table_name} "
                f"- {deleted_rows} registros removidos"
            )

        return responses

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

    def replace_snapshot_batches_paginated_delete(
        self,
        table_name,
        filters,
        data,
        batch_size=500,
        delete_batch_size=250,
        id_column="id"
    ):

        self.delete_where_batches(
            table_name=table_name,
            filters=filters,
            batch_size=delete_batch_size,
            id_column=id_column
        )

        if not data:
            return []

        return self.insert_batches(
            table_name=table_name,
            data=data,
            batch_size=batch_size
        )
