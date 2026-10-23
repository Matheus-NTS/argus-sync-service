"""Testes isolados do publicador da dimensao de clientes."""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
from pandas.testing import assert_frame_equal

from features.intelligence.profitability.profitability_channel_customers_publisher import (
    LOAD_TABLE,
    STAGE_TABLE,
    PUBLISH_RPC,
    ProfitabilityChannelCustomersPublisher,
    prepare_customers_payload,
)


def sample():
    return pd.DataFrame({
        "codigo_cliente_normalizado": ["101", "102", "103"],
        "segmento": ["Atacado", "Varejo", "N\\u00e3o classificados"],
    })


def connector():
    result = MagicMock()
    result.client.rpc.return_value.execute.return_value = (
        SimpleNamespace(data=3)
    )
    return result


class ChannelCustomersPublisherTests(unittest.TestCase):

    def test_payload_and_no_mutation(self):
        source = sample()
        original = source.copy(deep=True)

        rows = prepare_customers_payload(source)

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            set(rows[0]),
            {"codigo_cliente_normalizado", "segmento"},
        )
        assert_frame_equal(source, original)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            prepare_customers_payload(sample().iloc[:0])

    def test_duplicate_rejected(self):
        source = sample()
        source.loc[1, "codigo_cliente_normalizado"] = "101"

        with self.assertRaises(ValueError):
            prepare_customers_payload(source)

    def test_invalid_segment_rejected(self):
        source = sample()
        source.loc[0, "segmento"] = "Outro"

        with self.assertRaises(ValueError):
            prepare_customers_payload(source)

    def test_missing_column_rejected(self):
        with self.assertRaises(ValueError):
            prepare_customers_payload(
                sample().drop(columns=["segmento"])
            )

    def test_invalid_batch_size_rejected(self):
        for size in (0, -1, True, 1.5):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    ProfitabilityChannelCustomersPublisher(
                        connector(), batch_size=size
                    )

    def test_naive_timestamp_rejected_before_write(self):
        db = connector()
        publisher = ProfitabilityChannelCustomersPublisher(db)

        with self.assertRaises(ValueError):
            publisher.publish(
                sample(),
                source_as_of=datetime(2026, 10, 23),
            )

        db.insert.assert_not_called()
        db.insert_batches.assert_not_called()
        db.client.rpc.assert_not_called()

    def test_success_uses_existing_connector(self):
        db = connector()
        publisher = ProfitabilityChannelCustomersPublisher(
            db, batch_size=2
        )
        source = sample()
        original = source.copy(deep=True)

        result = publisher.publish(
            source,
            source_as_of=datetime(
                2026, 10, 23, tzinfo=timezone.utc
            ),
        )

        self.assertEqual(result["expected_rows"], 3)

        args, _ = db.insert.call_args
        self.assertEqual(args[0], LOAD_TABLE)
        self.assertEqual(args[1]["expected_rows"], 3)

        args, kwargs = db.insert_batches.call_args
        self.assertEqual(args[0], STAGE_TABLE)
        self.assertEqual(len(args[1]), 3)
        self.assertEqual(kwargs["batch_size"], 2)

        self.assertTrue(all(
            row["run_id"] == result["run_id"]
            for row in args[1]
        ))

        db.client.rpc.assert_called_once_with(
            PUBLISH_RPC,
            {"p_run_id": result["run_id"]},
        )
        assert_frame_equal(source, original)

    def test_staging_failure_never_calls_rpc(self):
        db = connector()
        db.insert_batches.side_effect = RuntimeError("stage failure")

        publisher = ProfitabilityChannelCustomersPublisher(db)

        with self.assertRaisesRegex(
            RuntimeError, "STAGING_FAILED"
        ):
            publisher.publish(
                sample(),
                source_as_of=datetime(
                    2026, 10, 23, tzinfo=timezone.utc
                ),
            )

        db.client.rpc.assert_not_called()

    def test_rpc_failure_is_unconfirmed(self):
        db = connector()
        db.client.rpc.return_value.execute.side_effect = (
            RuntimeError("rpc failure")
        )

        publisher = ProfitabilityChannelCustomersPublisher(db)

        with self.assertRaisesRegex(
            RuntimeError, "PUBLICATION_UNCONFIRMED"
        ):
            publisher.publish(
                sample(),
                source_as_of=datetime(
                    2026, 10, 23, tzinfo=timezone.utc
                ),
            )

    def test_unexpected_rpc_result_is_unconfirmed(self):
        db = connector()
        db.client.rpc.return_value.execute.return_value = (
            SimpleNamespace(data=2)
        )

        publisher = ProfitabilityChannelCustomersPublisher(db)

        with self.assertRaisesRegex(
            RuntimeError, "PUBLICATION_UNCONFIRMED"
        ):
            publisher.publish(
                sample(),
                source_as_of=datetime(
                    2026, 10, 23, tzinfo=timezone.utc
                ),
            )


if __name__ == "__main__":
    unittest.main()
