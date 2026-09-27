import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

from runbook_kit.checks import run_runbook, load_runbook


def book(kind, target, **extra):
    return {"name": "Synthetic", "owner": "Example", "severity": "low", "steps": [dict(name="Check", type=kind, target=target, **extra)]}


class BoundaryTests(unittest.TestCase):
    def test_network_default_denied(self):
        with patch("runbook_kit.checks.build_opener"), self.assertRaises(ValueError):
            run_runbook(book("http_status", "https://example.invalid"))

    def test_unsafe_urls_rejected_before_open(self):
        targets = ["file:///etc/passwd", "ftp://example.invalid/x", "https://user:secret@example.invalid", "https://other.invalid", "https://example.invalid.evil.test", "https://example.invalid\\@other.invalid", "https://example.invalid/\npath", "https://example.invalid:99999", "https://example.invalid/#fragment"]
        for target in targets:
            with self.subTest(target=target), patch("runbook_kit.checks.build_opener") as opener:
                with self.assertRaises(ValueError):
                    run_runbook(book("http_status", target), allowed_hosts=["example.invalid"])
                opener.assert_not_called()

    def test_allowlisted_request_uses_no_redirect_handler(self):
        from runbook_kit.checks import _NoRedirect
        response = MagicMock()
        response.__enter__.return_value.status = 200
        with patch("runbook_kit.checks.build_opener") as build:
            build.return_value.open.return_value = response
            results = run_runbook(book("http_status", "https://EXAMPLE.invalid/health"), allowed_hosts=["example.invalid"])
        self.assertTrue(results[0]["passed"])
        self.assertTrue(any(isinstance(x, _NoRedirect) for x in build.call_args.args))
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.invalid"))
        response.read.assert_not_called()

    def test_redirect_is_failed_without_following(self):
        with patch("runbook_kit.checks.build_opener") as build:
            build.return_value.open.side_effect = HTTPError("https://example.invalid", 302, "redirect", {}, None)
            result = run_runbook(book("http_status", "https://example.invalid"), allowed_hosts=["example.invalid"])
        self.assertFalse(result[0]["passed"])
        self.assertEqual(build.return_value.open.call_count, 1)

    def test_path_escape_and_special_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for target in ("../outside", str(Path(tmp).parent / "outside"), "\\\\server\\share\\file", "file.txt:stream", "NUL", "dir/CON.txt"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    run_runbook(book("file_exists", target), Path(tmp))

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            link = Path(tmp) / "link"
            try:
                link.symlink_to(other, target_is_directory=True)
            except OSError:
                self.skipTest("OS does not permit creating test symlinks")
            with self.assertRaises(ValueError):
                run_runbook(book("file_exists", "link"), Path(tmp))

    def test_bounded_file_read_rejects_oversized_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "fixture").write_bytes(b"needle and more")
            with self.assertRaises(ValueError):
                run_runbook(book("file_contains", "fixture", contains="needle"), Path(tmp), max_file_bytes=5)
            self.assertTrue(run_runbook(book("file_contains", "fixture", contains="needle"), Path(tmp), max_file_bytes=20)[0]["passed"])

    def test_all_steps_preflight_before_network(self):
        runbook = book("http_status", "https://example.invalid")
        runbook["steps"].append(dict(name="Escape", type="file_exists", target="../outside"))
        with patch("runbook_kit.checks.build_opener") as build, self.assertRaises(ValueError):
            run_runbook(runbook, allowed_hosts=["example.invalid"])
        build.assert_not_called()

    def test_runbook_document_read_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "large.json"
            target.write_bytes(b" " * (1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                load_runbook(target)


    def test_cli_validate_obeys_operator_policy(self):
        import contextlib
        import io
        import json
        from runbook_kit.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book.json"
            path.write_text(json.dumps(book("http_status", "https://example.invalid")))
            for options, expected in (([], 2), (["--allow-host", "example.invalid"], 0)):
                with patch("sys.argv", ["kit", "validate", str(path), *options]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(), expected)

    def test_policy_cannot_be_granted_by_runbook(self):
        runbook = book("http_status", "https://example.invalid")
        runbook["allowed_hosts"] = ["example.invalid"]
        with patch("runbook_kit.checks.build_opener"), self.assertRaises(ValueError):
            run_runbook(runbook)

    def test_reader_requests_only_limit_plus_one(self):
        from runbook_kit.checks import _read_bounded
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fixture"
            target.write_bytes(b"safe")
            with patch.object(Path, "open") as opened:
                opened.return_value.__enter__.return_value.read.return_value = b"safe"
                self.assertEqual(_read_bounded(target, 10), b"safe")
            opened.return_value.__enter__.return_value.read.assert_called_once_with(11)

    def test_invalid_byte_limit_rejected(self):
        for limit in (0, -1, True, 16777217):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                run_runbook(book("file_exists", "fixture"), max_file_bytes=limit)
