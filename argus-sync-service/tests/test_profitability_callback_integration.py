"""Contrato estrutural da extensao de rentabilidade."""

import ast
import unittest
from pathlib import Path


SOURCE = Path("pipelines/profitability_pipeline.py")


class ProfitabilityCallbackIntegrationTests(unittest.TestCase):

    def test_callback_runs_after_official_monthly_persistence(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))

        pipeline_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "ProfitabilityPipeline"
        )

        run_method = next(
            node for node in pipeline_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "run"
        )

        monthly_saves = []
        callback_calls = []
        returns = []

        for node in ast.walk(run_method):
            if isinstance(node, ast.Call):
                func = node.func

                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "_save_monthly_snapshot"
                ):
                    monthly_saves.append(node.lineno)

                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "on_dataset_ready"
                ):
                    callback_calls.append(node.lineno)

            elif isinstance(node, ast.Return):
                returns.append(node.lineno)

        self.assertEqual(len(monthly_saves), 1)
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(len(returns), 1)

        self.assertLess(monthly_saves[0], callback_calls[0])
        self.assertLess(callback_calls[0], returns[0])


if __name__ == "__main__":
    unittest.main()
