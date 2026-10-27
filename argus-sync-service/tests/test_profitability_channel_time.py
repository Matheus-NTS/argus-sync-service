"""Testes da referencia temporal do canal."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from features.intelligence.profitability.profitability_channel_time import (
    get_channel_source_as_of,
)


class ProfitabilityChannelTimeTests(unittest.TestCase):

    def test_uses_server_time_with_margin(self):
        connector = Mock()
        connector.client.rpc.return_value.execute.return_value.data = (
            "2026-10-26T18:00:00+00:00"
        )

        result = get_channel_source_as_of(connector)

        self.assertEqual(
            result,
            datetime(
                2026, 10, 26, 17, 59, 55,
                tzinfo=timezone.utc,
            ),
        )

        connector.client.rpc.assert_called_once_with(
            "argus_channel_server_time",
            {},
        )

    def test_rejects_invalid_response(self):
        connector = Mock()
        connector.client.rpc.return_value.execute.return_value.data = None

        with self.assertRaisesRegex(
            ValueError,
            "ARGUS_CHANNEL_SERVER_TIME_INVALID",
        ):
            get_channel_source_as_of(connector)

    def test_rejects_timestamp_without_timezone(self):
        connector = Mock()
        connector.client.rpc.return_value.execute.return_value.data = (
            "2026-10-26T18:00:00"
        )

        with self.assertRaisesRegex(
            ValueError,
            "Timestamp sem timezone",
        ):
            get_channel_source_as_of(connector)


    def test_rejects_clock_mismatch_before_publication(self):
        connector = Mock()

        future_server_time = (
            datetime.now(timezone.utc)
            + timedelta(minutes=2)
        )

        connector.client.rpc.return_value.execute.return_value.data = (
            future_server_time.isoformat()
        )

        with self.assertRaisesRegex(
            ValueError,
            "ARGUS_CHANNEL_CLOCK_MISMATCH",
        ):
            get_channel_source_as_of(connector)


if __name__ == "__main__":
    unittest.main()
