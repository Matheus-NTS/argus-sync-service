"""Testes sem banco ou rede. Executar via unittest."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd

from features.intelligence.profitability.profitability_channel_publisher import (
    ProfitabilityChannelPublisher,
    prepare_channel_payload,
)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([{
            "data_venda": "2026-10-16",
            "empresa_key": "NTS Rio",
            "vendedor": "VENDEDOR",
            "codigo_cliente_normalizado": "123",
            "segmento": "Atacado",
            "faturamento_analisavel": 100.0,
            "custo_analisavel": 60.0,
            "lucro_analisavel": 40.0,
            "margem_percentual": 40.0,
            "markup_percentual": 66.666,
        }])
        self.connector = Mock()
        self.connector.client.rpc.return_value.execute.return_value = SimpleNamespace(data=1)
        self.publisher = ProfitabilityChannelPublisher(self.connector)
        self.timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)

    def test_payload_only_persisted_columns_and_no_mutation(self):
        original = self.frame.copy(deep=True)
        rows, totals = prepare_channel_payload(self.frame)
        self.assertEqual(totals["expected_rows"], 1)
        self.assertEqual(totals["expected_profit"], 40.0)
        self.assertNotIn("margem_percentual", rows[0])
        pd.testing.assert_frame_equal(original, self.frame)

    def test_success_calls_existing_connector_and_rpc(self):
        result = self.publisher.publish(self.frame, source_as_of=self.timestamp)
        self.assertEqual(result["expected_rows"], 1)
        self.connector.insert.assert_called_once()
        self.connector.insert_batches.assert_called_once()
        self.connector.client.rpc.assert_called_once_with(
            "argus_publish_profitability_channel", {"p_run_id": result["run_id"]}
        )

    def test_nonfinite_rejected_before_write(self):
        self.frame.loc[0, "lucro_analisavel"] = float("inf")
        with self.assertRaises(ValueError):
            self.publisher.publish(self.frame, source_as_of=self.timestamp)
        self.connector.insert.assert_not_called()

    def test_duplicate_grain_rejected_before_write(self):
        duplicate = pd.concat([self.frame, self.frame], ignore_index=True)
        with self.assertRaises(ValueError):
            self.publisher.publish(duplicate, source_as_of=self.timestamp)
        self.connector.insert.assert_not_called()

    def test_staging_failure_never_calls_rpc(self):
        self.connector.insert_batches.side_effect = RuntimeError("Falha no lote")
        with self.assertRaises(RuntimeError):
            self.publisher.publish(self.frame, source_as_of=self.timestamp)
        self.connector.client.rpc.assert_not_called()

    def test_rpc_error_propagates(self):
        self.connector.client.rpc.return_value.execute.side_effect = RuntimeError("Rollback")

        with self.assertRaisesRegex(
            RuntimeError, "ARGUS_CHANNEL_PUBLICATION_UNCONFIRMED"
        ) as context:
            self.publisher.publish(self.frame, source_as_of=self.timestamp)

        load = self.connector.insert.call_args.args[1]
        run_id = load["run_id"]

        self.assertIn(f"run_id={run_id}", str(context.exception))
        self.assertIsInstance(context.exception.__cause__, RuntimeError)
        self.connector.client.rpc.assert_called_once_with(
            "argus_publish_profitability_channel",
            {"p_run_id": run_id},
        )
        self.connector.client.rpc.return_value.execute.assert_called_once()

    def test_unexpected_rpc_return_fails(self):
        self.connector.client.rpc.return_value.execute.return_value = SimpleNamespace(data=0)
        with self.assertRaises(RuntimeError):
            self.publisher.publish(self.frame, source_as_of=self.timestamp)

    def test_naive_timestamp_rejected_before_write(self):
        with self.assertRaises(ValueError):
            self.publisher.publish(self.frame, source_as_of=datetime(2026, 10, 16))
        self.connector.insert.assert_not_called()

    def test_empty_rejected_before_write(self):
        with self.assertRaises(ValueError):
            self.publisher.publish(self.frame.iloc[:0], source_as_of=self.timestamp)
        self.connector.insert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
