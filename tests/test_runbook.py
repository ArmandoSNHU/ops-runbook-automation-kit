import tempfile
import unittest
from pathlib import Path

from runbook_kit import render_markdown_report, run_runbook, validate_runbook


class RunbookKitTests(unittest.TestCase):
    def test_validate_runbook_requires_fields(self):
        errors = validate_runbook({"name": "Incomplete"})

        self.assertIn("Missing required field: owner", errors)
        self.assertIn("Missing required field: steps", errors)

    def test_file_checks_pass_and_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("Verification steps", encoding="utf-8")
            runbook = {
                "name": "Test",
                "owner": "Ops",
                "severity": "low",
                "steps": [
                    {"name": "Exists", "type": "file_exists", "target": "README.md"},
                    {"name": "Contains", "type": "file_contains", "target": "README.md", "contains": "Verification"},
                    {"name": "Missing text", "type": "file_contains", "target": "README.md", "contains": "Nope"},
                ],
            }

            results = run_runbook(runbook, root)

        self.assertTrue(results[0]["passed"])
        self.assertTrue(results[1]["passed"])
        self.assertFalse(results[2]["passed"])

    def test_render_markdown_report(self):
        runbook = {"name": "Test", "owner": "Ops", "severity": "low", "steps": []}
        report = render_markdown_report(
            runbook,
            [{"name": "Check", "type": "file_exists", "passed": True, "evidence": "ok"}],
        )

        self.assertIn("# Runbook Report: Test", report)
        self.assertIn("| Check | file_exists | PASS | ok |", report)


if __name__ == "__main__":
    unittest.main()

