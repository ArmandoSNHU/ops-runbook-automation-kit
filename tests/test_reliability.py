import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runbook_kit import validate_runbook, render_markdown_report
from runbook_kit.cli import main


def book(steps=None):
    return {"name": "Synthetic", "owner": "Example Ops", "severity": "low",
            "steps": steps if steps is not None else [{"name": "Check", "type": "file_exists", "target": "fixture.txt"}]}


class ReliabilityTests(unittest.TestCase):
    def invoke(self, command, content, fixture=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "examples").mkdir()
            path = root / "examples" / "runbook.json"
            path.write_text(content, encoding="utf-8")
            if fixture:
                (root / "fixture.txt").write_text("synthetic evidence", encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with patch("sys.argv", ["runbook-kit", command, str(path)]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main()
            return code, out.getvalue(), err.getvalue()

    def test_success_exit_and_json_contract(self):
        code, out, err = self.invoke("run", json.dumps(book()))
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)[0]["passed"])
        self.assertEqual(err, "")

    def test_failed_checks_return_one_and_keep_report(self):
        for command in ("run", "render"):
            with self.subTest(command=command):
                code, out, err = self.invoke(command, json.dumps(book()), fixture=False)
                self.assertEqual(code, 1)
                self.assertIn('false' if command == 'run' else 'REVIEW', out)
                self.assertEqual(err, "")

    def test_invalid_json_is_sanitized_for_all_commands(self):
        for command in ("validate", "run", "render"):
            with self.subTest(command=command):
                code, out, err = self.invoke(command, '{PRIVATE_MARKER')
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("ERROR:", err)
                self.assertNotIn("PRIVATE_MARKER", err)
                self.assertNotIn("Traceback", err)

    def test_invalid_schema_never_executes(self):
        with patch("runbook_kit.cli.run_runbook") as run:
            for command in ("validate", "run", "render"):
                code, out, err = self.invoke(command, json.dumps(book([])))
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("ERROR:", err)
            run.assert_not_called()

    def test_malformed_shapes_return_errors_without_exception(self):
        values = [None, [], 1, "private", book([]), book([None]), book([[]]), book([{"type": []}])]
        for value in values:
            with self.subTest(value=value):
                self.assertTrue(validate_runbook(value))

    def test_required_strings_and_contains(self):
        for field in ("name", "owner", "severity"):
            for value in (None, 7, "", "   "):
                invalid = book()
                invalid[field] = value
                self.assertTrue(validate_runbook(invalid))
        for field in ("name", "type", "target", "contains"):
            for value in (None, [], "", "   "):
                step = {"name": "Check", "type": "file_contains", "target": "fixture.txt", "contains": "evidence"}
                step[field] = value
                self.assertTrue(validate_runbook(book([step])))
        self.assertTrue(validate_runbook(book([{"name": "Check", "type": "file_contains", "target": "fixture.txt"}])))

    def test_http_status_type_and_range(self):
        for value in (True, "200", 99, 600, None, [], 200.5):
            self.assertTrue(validate_runbook(book([{"name": "HTTP", "type": "http_status", "target": "https://example.invalid", "status": value}])))
        self.assertEqual(validate_runbook(book([{"name": "HTTP", "type": "http_status", "target": "https://example.invalid"}])), [])

    def test_empty_results_do_not_report_pass(self):
        self.assertIn("Overall status: REVIEW", render_markdown_report(book(), []))

    def test_unreadable_runbook_is_sanitized(self):
        out, err = io.StringIO(), io.StringIO()
        with patch("sys.argv", ["runbook-kit", "run", "PRIVATE_MARKER.json"]), patch("runbook_kit.cli.load_runbook", side_effect=OSError("PRIVATE_MARKER")), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("PRIVATE_MARKER", err.getvalue())

    def test_execution_access_error_is_sanitized(self):
        with patch("runbook_kit.cli.run_runbook", side_effect=PermissionError("PRIVATE_MARKER")):
            code, out, err = self.invoke("run", json.dumps(book()))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotIn("PRIVATE_MARKER", err)
