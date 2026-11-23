"""Focused tests for :mod:`safepath.core` using only the standard library."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from safepath import (  # noqa: E402
    Reason,
    SafePathResolver,
    UnsafePathError,
    safe_join,
    sanitize_filename,
)


class PathTestBase(unittest.TestCase):
    """Provide an isolated temporary directory for each test."""

    def setUp(self) -> None:
        """Create a fresh directory and register its cleanup."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.base = self.root / "uploads"
        self.base.mkdir()

    def assert_reason(self, reason: str, call: object, *args: object) -> None:
        """Assert that calling ``call`` raises ``UnsafePathError`` with ``reason``.

        Args:
            reason: Expected machine-readable reason code.
            call: Callable under test.
            *args: Positional arguments forwarded to the callable.
        """
        with self.assertRaises(UnsafePathError) as caught:
            call(*args)  # type: ignore[operator]
        self.assertEqual(caught.exception.reason, reason)

    def symlink(self, target: Path, link: Path) -> None:
        """Create a directory symlink, falling back to a Windows junction.

        Args:
            target: Existing directory the link points to.
            link: Path of the symlink to create.
        """
        try:
            os.symlink(target, link, target_is_directory=True)
            return
        except (OSError, NotImplementedError, AttributeError):
            pass

        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return
            self.skipTest(f"junctions unavailable on this system: {result.stderr.strip()}")
        self.skipTest("symlinks unavailable on this system")


class SafeJoinTests(PathTestBase):
    """Tests for the one-shot ``safe_join`` function."""

    def test_joins_ordinary_relative_path(self) -> None:
        result = safe_join(self.base, "reports", "2026.csv")
        self.assertEqual(result, (self.base / "reports" / "2026.csv").resolve())

    def test_accepts_dot_component(self) -> None:
        self.assertEqual(safe_join(self.base, ".", "ok.txt"), (self.base / "ok.txt").resolve())

    def test_rejects_simple_traversal(self) -> None:
        self.assert_reason(Reason.TRAVERSAL, safe_join, self.base, "../secret.txt")

    def test_rejects_traversal_hidden_in_middle(self) -> None:
        self.assert_reason(Reason.TRAVERSAL, safe_join, self.base, "a", "..", "b")

    def test_rejects_root_relative_path(self) -> None:
        self.assert_reason(Reason.ABSOLUTE_PATH, safe_join, self.base, "/etc/passwd")

    def test_rejects_windows_drive_path(self) -> None:
        self.assert_reason(Reason.ABSOLUTE_PATH, safe_join, self.base, "C:\\Windows\\win.ini")

    def test_rejects_windows_drive_relative_path(self) -> None:
        self.assert_reason(Reason.ABSOLUTE_PATH, safe_join, self.base, "C:secret.txt")

    def test_rejects_unc_path(self) -> None:
        unc = "\\\\server\\share\\secret.txt"
        self.assert_reason(Reason.ABSOLUTE_PATH, safe_join, self.base, unc)

    def test_rejects_forward_slash_unc_path(self) -> None:
        self.assert_reason(Reason.ABSOLUTE_PATH, safe_join, self.base, "//server/share/secret")

    def test_rejects_backslash_separators(self) -> None:
        self.assert_reason(Reason.TRAVERSAL, safe_join, self.base, "..\\..\\secret.txt")

    def test_rejects_absolute_later_part(self) -> None:
        self.assert_reason(Reason.ABSOLUTE_PATH, safe_join, self.base, "a", "/etc/passwd")

    def test_rejects_drive_qualified_later_part(self) -> None:
        self.assert_reason(Reason.ABSOLUTE_PATH, safe_join, self.base, "a", "D:secret.txt")

    def test_rejects_encoded_dotdot(self) -> None:
        self.assert_reason(Reason.ENCODED_TRAVERSAL, safe_join, self.base, "%2e%2e/secret.txt")

    def test_rejects_encoded_separator(self) -> None:
        self.assert_reason(Reason.ENCODED_TRAVERSAL, safe_join, self.base, "..%2fsecret.txt")

    def test_rejects_encoded_backslash(self) -> None:
        self.assert_reason(Reason.ENCODED_TRAVERSAL, safe_join, self.base, "a%5Cb")

    def test_decodes_only_once(self) -> None:
        result = safe_join(self.base, "%252e%252e")
        self.assertEqual(result.name, "%2e%2e")
        self.assertEqual(result.parent, self.base)

    def test_rejects_nul_byte(self) -> None:
        self.assert_reason(Reason.NUL_BYTE, safe_join, self.base, "file\x00.txt")

    def test_rejects_encoded_nul_byte(self) -> None:
        self.assert_reason(Reason.NUL_BYTE, safe_join, self.base, "file%00.txt")

    def test_rejects_invalid_percent_encoding(self) -> None:
        self.assert_reason(Reason.INVALID_ENCODING, safe_join, self.base, "file%FF.txt")

    def test_rejects_empty_path(self) -> None:
        self.assert_reason(Reason.EMPTY_PATH, safe_join, self.base, "")

    def test_rejects_dot_only_path(self) -> None:
        self.assert_reason(Reason.EMPTY_PATH, safe_join, self.base, "./")

    def test_requires_at_least_one_part(self) -> None:
        self.assert_reason(Reason.EMPTY_PATH, safe_join, self.base)

    def test_rejects_non_text_path(self) -> None:
        with self.assertRaises(TypeError):
            safe_join(self.base, b"bytes.txt")  # type: ignore[arg-type]


class ResolverTests(PathTestBase):
    """Tests for :class:`SafePathResolver` behaviour and symlink handling."""

    def test_base_property_is_absolute(self) -> None:
        resolver = SafePathResolver(self.base, strict=False)
        self.assertTrue(resolver.base.is_absolute())
        self.assertEqual(resolver.base, self.base)

    def test_is_safe_accepts_clean_path(self) -> None:
        resolver = SafePathResolver(self.base, strict=False)
        self.assertTrue(resolver.is_safe("notes.txt"))
        self.assertFalse(resolver.is_safe("../notes.txt"))

    def test_is_safe_accepts_missing_file(self) -> None:
        resolver = SafePathResolver(self.base)
        self.assertTrue(resolver.is_safe("new-file.txt"))

    def test_pathlike_user_path(self) -> None:
        resolver = SafePathResolver(self.base, strict=False)
        self.assertEqual(resolver.resolve(Path("notes.txt")), (self.base / "notes.txt").resolve())

    def test_strict_resolver_requires_existing_target(self) -> None:
        target = self.base / "exists.txt"
        target.touch()
        resolver = SafePathResolver(self.base, strict=True)
        self.assertEqual(resolver.resolve("exists.txt"), target.resolve())
        with self.assertRaises(FileNotFoundError):
            resolver.resolve("missing.txt")

    def test_non_strict_resolver_allows_missing_target(self) -> None:
        resolver = SafePathResolver(self.base, strict=False)
        self.assertEqual(resolver.resolve("new.txt"), (self.base / "new.txt").resolve())

    def test_rejects_symlink_escape(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        self.symlink(outside, self.base / "escape")
        resolver = SafePathResolver(self.base, strict=False)
        self.assert_reason(Reason.SYMLINK_ESCAPE, resolver.resolve, "escape/secret.txt")

    def test_is_safe_never_follows_escaping_symlink(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        self.symlink(outside, self.base / "escape")
        resolver = SafePathResolver(self.base, strict=False)
        self.assertFalse(resolver.is_safe("escape/secret.txt"))

    def test_allows_symlink_staying_inside_base(self) -> None:
        real = self.base / "real"
        real.mkdir()
        (real / "ok.txt").write_text("ok", encoding="utf-8")
        self.symlink(real, self.base / "inside")
        resolver = SafePathResolver(self.base, strict=False)
        self.assertEqual(resolver.resolve("inside/ok.txt"), (real / "ok.txt").resolve())

    def test_allow_symlinks_flag_permits_escape(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("secret", encoding="utf-8")
        self.symlink(outside, self.base / "escape")
        resolver = SafePathResolver(self.base, allow_symlinks=True, strict=False)
        self.assertEqual(resolver.resolve("escape/secret.txt"), (outside / "secret.txt").resolve())

    def test_symlinked_base_is_trusted(self) -> None:
        real = self.root / "real-base"
        real.mkdir()
        (real / "ok.txt").write_text("ok", encoding="utf-8")
        link = self.root / "base-link"
        self.symlink(real, link)
        resolver = SafePathResolver(link, strict=False)
        self.assertEqual(resolver.resolve("ok.txt"), (real / "ok.txt").resolve())

    def test_sibling_directory_is_not_confused_with_base(self) -> None:
        sibling = self.root / "uploads-old"
        sibling.mkdir()
        (sibling / "secret.txt").write_text("secret", encoding="utf-8")
        resolver = SafePathResolver(self.base, strict=False)
        self.assertFalse(resolver.is_safe("../uploads-old/secret.txt"))
        self.assert_reason(Reason.TRAVERSAL, resolver.resolve, "../uploads-old/secret.txt")

    def test_unicode_and_spaces_are_allowed(self) -> None:
        resolver = SafePathResolver(self.base, strict=False)
        expected = (self.base / "café report 2026.txt").resolve()
        self.assertEqual(resolver.resolve("café report 2026.txt"), expected)


class SanitizeTests(unittest.TestCase):
    """Tests for :func:`sanitize_filename`."""

    def test_strips_posix_directories(self) -> None:
        self.assertEqual(sanitize_filename("/etc/passwd/notes.txt"), "notes.txt")

    def test_strips_windows_directories(self) -> None:
        self.assertEqual(sanitize_filename("..\\..\\CON.txt"), "_CON.txt")

    def test_removes_control_characters_and_nul(self) -> None:
        self.assertEqual(sanitize_filename("re\x00port\x01.txt"), "re_port_.txt")

    def test_neutralises_reserved_names(self) -> None:
        reserved = ["CON", "con.txt", "PRN", "AUX", "NUL", "COM1", "com9.log", "LPT3", "lpt9.txt"]
        for name in reserved:
            with self.subTest(name=name):
                sanitized = sanitize_filename(name)
                stem = sanitized.split(".", 1)[0].upper()
                self.assertNotIn(stem, reserved)

    def test_trims_trailing_dots_and_spaces(self) -> None:
        self.assertEqual(sanitize_filename("report.txt...  "), "report.txt")

    def test_preserves_extension_when_truncating(self) -> None:
        result = sanitize_filename("a" * 300 + ".txt", max_length=20)
        self.assertEqual(len(result), 20)
        self.assertTrue(result.endswith(".txt"))

    def test_empty_name_uses_replacement(self) -> None:
        self.assertEqual(sanitize_filename(""), "_")
        self.assertEqual(sanitize_filename("..."), "_")
        self.assertEqual(sanitize_filename("...", replacement="unnamed"), "unnamed")

    def test_rejects_unsafe_replacement(self) -> None:
        for replacement in ("a/b", "a\\b", "a\x00b", "a\nb", ""):
            with self.subTest(replacement=replacement):
                if replacement == "":
                    self.assertEqual(sanitize_filename("...", replacement=""), "unnamed")
                else:
                    with self.assertRaises(ValueError):
                        sanitize_filename("x.txt", replacement=replacement)

    def test_rejects_invalid_max_length(self) -> None:
        for value in (0, -1, 2.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sanitize_filename("x.txt", max_length=value)  # type: ignore[arg-type]

    def test_rejects_non_string_name(self) -> None:
        with self.assertRaises(TypeError):
            sanitize_filename(123)  # type: ignore[arg-type]

    def test_preserves_unicode_and_spaces(self) -> None:
        self.assertEqual(sanitize_filename("café report.txt"), "café report.txt")


class ErrorTests(unittest.TestCase):
    """Tests for the public exception type."""

    def test_error_is_value_error_with_reason(self) -> None:
        error = UnsafePathError("bad", Reason.TRAVERSAL)
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.reason, "traversal")
        self.assertEqual(str(error), "bad")

    def test_repr_includes_reason(self) -> None:
        self.assertIn("reason='traversal'", repr(UnsafePathError("bad", Reason.TRAVERSAL)))


if __name__ == "__main__":
    unittest.main()
