"""Testes isolados da sincronizacao financeira por canal."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd

from features.intelligence.profitability.profitability_channel_sync import (
    sync_profitability_channel,
)


MODULE = (
    "features.intelligence.profitability."
    "profitability_channel_sync"
)


class ProfitabilityChannelSyncTests(unittest.TestCase):

    @patch(f"{MODULE}.ProfitabilityChannelPublisher")
    @patch(f"{MODULE}.build_profitability_channel_snapshot")
    def test_valid_snapshot_is_published(
        self, build_mock, publisher_class
    ):
        sql_connector = object()
        supabase_connector = object()

        snapshot = pd.DataFrame({
            "segmento": ["Atacado"],
            "faturamento_analisavel": [100.0],
        })
        source_as_of = datetime.now(timezone.utc)

        build_mock.return_value = (snapshot, source_as_of)

        publisher = publisher_class.return_value
        publisher.publish.return_value = {
            "run_id": "test-run",
            "expected_rows": 1,
        }

        result = sync_profitability_channel(
            sql_connector,
            supabase_connector,
        )

        build_mock.assert_called_once_with(sql_connector)
        publisher_class.assert_called_once_with(supabase_connector)
        publisher.publish.assert_called_once()

        args, kwargs = publisher.publish.call_args

        self.assertIs(args[0], snapshot)
        self.assertEqual(kwargs["source_as_of"], source_as_of)
        self.assertEqual(result["expected_rows"], 1)

    @patch(f"{MODULE}.ProfitabilityChannelPublisher")
    @patch(f"{MODULE}.build_profitability_channel_snapshot")
    def test_extraction_failure_blocks_publication(
        self, build_mock, publisher_class
    ):
        build_mock.side_effect = RuntimeError("SQL unavailable")

        with self.assertRaisesRegex(RuntimeError, "SQL unavailable"):
            sync_profitability_channel(
                object(),
                object(),
            )

        publisher_class.assert_not_called()

    @patch(f"{MODULE}.ProfitabilityChannelPublisher")
    @patch(f"{MODULE}.build_profitability_channel_snapshot")
    def test_publication_failure_is_propagated(
        self, build_mock, publisher_class
    ):
        build_mock.return_value = (
            pd.DataFrame({"segmento": ["Atacado"]}),
            datetime.now(timezone.utc),
        )

        publisher_class.return_value.publish.side_effect = (
            RuntimeError("Publication failed")
        )

        with self.assertRaisesRegex(
            RuntimeError, "Publication failed"
        ):
            sync_profitability_channel(
                object(),
                object(),
            )


if __name__ == "__main__":
    unittest.main()
