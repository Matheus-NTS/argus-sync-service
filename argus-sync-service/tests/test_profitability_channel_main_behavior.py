import os
import unittest
from unittest.mock import MagicMock, patch

import main as argus_main


class StopAfterProfitability(Exception):
    pass


class ChannelMainBehaviorTests(unittest.TestCase):

    def run_scenario(self, enabled):
        observed = {}

        def make_profitability(sql, supabase):
            pipeline = MagicMock()
            pipeline.on_dataset_ready = None

            def execute():
                observed["callback"] = pipeline.on_dataset_ready
                raise StopAfterProfitability()

            pipeline.run.side_effect = execute
            return pipeline

        env = {"ARGUS_PROFITABILITY_CHANNEL_ENABLED": "1" if enabled else "0"}

        with patch.dict(os.environ, env):
            with (
                patch.object(argus_main, "SQLServerConnector"),
                patch.object(argus_main, "SupabaseConnector"),
                patch.object(argus_main, "GoogleSheetsConnector"),
                patch.object(argus_main, "SalesPipeline"),
                patch.object(argus_main, "CustomerGeoPipeline"),
                patch.object(argus_main, "StockPipeline"),
                patch.object(
                    argus_main,
                    "ProfitabilityPipeline",
                    side_effect=make_profitability,
                ),
                patch.object(
                    argus_main,
                    "ProfitabilityChannelCoordinator",
                ) as coordinator,
                patch.object(
                    argus_main,
                    "mark_pipeline_success",
                ),
            ):
                with self.assertRaises(StopAfterProfitability):
                    argus_main.main()

                observed["coordinator_calls"] = coordinator.call_count

                if coordinator.called:
                    observed["coordinator_instance"] = coordinator.return_value

        return observed

    def test_disabled_does_not_register_callback(self):
        result = self.run_scenario(False)

        self.assertIsNone(result["callback"])
        self.assertEqual(result["coordinator_calls"], 0)

    def test_enabled_registers_coordinator(self):
        result = self.run_scenario(True)

        self.assertEqual(result["coordinator_calls"], 1)
        self.assertIs(
            result["callback"],
            result["coordinator_instance"],
        )


if __name__ == "__main__":
    unittest.main()
