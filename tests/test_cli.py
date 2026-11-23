"""Focused tests for :mod:`safepath.cli` using only the standard library."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from safepath import __version__  # noqa: E402
from safepath.cli import main  # noqa: E402


class CliTests(unittest.TestCase):
    """Exercise the ``check`` and ``sanitize`` subcommands in-process."""

    def setUp(self) -> None:
        """Create a temporary base directory for check commands."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()

    def test_check_accepts_safe_path(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["check", str(self.base), "reports/2026.csv"])
        self.assertEqual(code, 0)
        expected = (self.base / "reports" / "2026.csv").resolve()
        self.assertEqual(output.getvalue().strip(), str(expected))

    def test_check_rejects_traversal(self) -> None:
        errors = io.StringIO()
        with redirect_stderr(errors):
            code = main(["check", str(self.base), "../secret.txt"])
        self.assertEqual(code, 1)
        self.assertIn("[traversal]", errors.getvalue())

    def test_check_json_rejection(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["check", str(self.base), "%2e%2e/secret.txt", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason"], "encoded_traversal")

    def test_check_json_success(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["check", str(self.base), "ok.txt", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["path"], str((self.base / "ok.txt").resolve()))

    def test_sanitize_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["sanitize", "..\\..\\CON.txt"])
        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue().strip(), "_CON.txt")

    def test_version_flag(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            main(["--version"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn(__version__, output.getvalue())

    def test_missing_arguments_exit_with_usage_error(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["check"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
