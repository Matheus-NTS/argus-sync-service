"""Contrato estatico da migracao de clientes por canal."""

import re
import unittest
from pathlib import Path

from features.intelligence.profitability.profitability_channel_customers_publisher import (
    LOAD_TABLE,
    STAGE_TABLE,
    PUBLISH_RPC,
    SEGMENTS,
)

SQL_PATH = (
    Path(__file__).resolve().parents[1]
    / "sql"
    / "004_profitability_channel_customers.sql"
)


class ChannelCustomersSqlContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sql = SQL_PATH.read_text(encoding="utf-8")
        cls.normalized = re.sub(r"\s+", " ", cls.sql).lower()

    def test_python_contract_names(self):
        for table in (LOAD_TABLE, STAGE_TABLE):
            self.assertIn("create table public." + table, self.normalized)
        self.assertIn(
            "create table public.mart_profitability_channel_customers",
            self.normalized,
        )
        self.assertIn(
            "create function public." + PUBLISH_RPC + "(p_run_id uuid)",
            self.normalized,
        )

    def test_official_segments(self):
        for segment in SEGMENTS:
            self.assertEqual(
                self.sql.count("'" + segment + "'"),
                2,
            )

    def test_integrity_constraints(self):
        self.assertIn("run_id uuid primary key", self.normalized)
        self.assertIn("expected_rows > 0", self.normalized)
        self.assertIn(
            "primary key (run_id, codigo_cliente_normalizado)",
            self.normalized,
        )
        self.assertIn(
            "codigo_cliente_normalizado text primary key",
            self.normalized,
        )
        self.assertIn(
            "references public." + LOAD_TABLE + "(run_id)",
            self.normalized,
        )

    def test_transaction_and_publication(self):
        self.assertIn("begin;", self.normalized)
        self.assertTrue(self.normalized.rstrip().endswith("commit;"))
        self.assertIn("pg_advisory_xact_lock(62016, 2)", self.normalized)
        self.assertIn("share row exclusive mode", self.normalized)
        self.assertIn("for update", self.normalized)
        self.assertIn("source_as_of >= v_load.source_as_of", self.normalized)
        self.assertIn("v_count <> v_load.expected_rows", self.normalized)
        self.assertIn("v_inserted <> v_count", self.normalized)
        self.assertIn("v_published_count <> v_count", self.normalized)
        self.assertIn(
            "delete from public.mart_profitability_channel_customers;",
            self.normalized,
        )
        self.assertIn(
            "where run_id = p_run_id;",
            self.normalized,
        )

    def test_rls_and_permissions(self):
        for table in (
            LOAD_TABLE,
            STAGE_TABLE,
            "mart_profitability_channel_customers",
        ):
            self.assertIn(
                "public." + table + " enable row level security;",
                self.normalized,
            )

        self.assertIn(
            "create policy mart_profitability_channel_customers_select_authenticated",
            self.normalized,
        )
        self.assertIn("to authenticated using (true)", self.normalized)
        self.assertIn("security invoker", self.normalized)
        self.assertIn("set search_path to ''", self.normalized)
        self.assertIn(
            "grant execute on function public." + PUBLISH_RPC,
            self.normalized,
        )


if __name__ == "__main__":
    unittest.main()
