"""Contrato estrutural da integracao Atacado x Varejo no main.py."""

import ast
import unittest
from pathlib import Path


class ChannelMainIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        source = Path("main.py").read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        cls.main = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )

    def test_activation_flag_is_read_once(self):
        calls = [
            node
            for node in ast.walk(self.main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "getenv"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "ARGUS_PROFITABILITY_CHANNEL_ENABLED"
        ]
        self.assertEqual(len(calls), 1)

        assignments = [
            node
            for node in ast.walk(self.main)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "channel_enabled"
        ]
        self.assertEqual(len(assignments), 1)

        comparison = assignments[0].value
        self.assertIsInstance(comparison, ast.Compare)
        self.assertIsInstance(comparison.ops[0], ast.Eq)
        self.assertEqual(len(comparison.comparators), 1)
        self.assertIsInstance(comparison.comparators[0], ast.Constant)
        self.assertEqual(comparison.comparators[0].value, "1")
        self.assertIs(comparison.left, calls[0])

    def test_callback_registration_is_conditional(self):
        assignments = [
            node
            for node in ast.walk(self.main)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute)
                and target.attr == "on_dataset_ready"
                for target in node.targets
            )
        ]
        self.assertEqual(len(assignments), 1)

        guards = [
            node
            for node in ast.walk(self.main)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "channel_enabled"
            and assignments[0] in ast.walk(node)
        ]
        self.assertEqual(len(guards), 1)

    def test_channel_report_uses_same_flag(self):
        guards = [
            node
            for node in ast.walk(self.main)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "channel_enabled"
            and "RENTABILIDADE POR CANAL" in ast.unparse(node)
        ]
        self.assertEqual(len(guards), 1)

    def test_executive_remains_after_profitability(self):
        calls = [
            node
            for node in ast.walk(self.main)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run_timed"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ]

        positions = {
            node.args[0].value: node.lineno
            for node in calls
        }

        self.assertLess(
            positions["Profitability Pipeline"],
            positions["Executive Pipeline"],
        )


if __name__ == "__main__":
    unittest.main()
