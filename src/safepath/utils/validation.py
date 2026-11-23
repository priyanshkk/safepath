"""Input validation primitives used before any filesystem access."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote

from ..config import ENCODED_NUL, ENCODED_TRAVERSAL, SEPARATORS, WINDOWS_DRIVE
from ..errors import Reason, UnsafePathError


def as_text(path: str | os.PathLike[str]) -> str:
    """Convert a path-like value to text, rejecting bytes."""
    try:
        value: str | bytes = os.fspath(path)
    except TypeError as exc:
        raise TypeError("path must be str or os.PathLike[str]") from exc
    if isinstance(value, bytes):
        raise TypeError("byte paths are not supported; decode them first")
    return value


def decode_once(raw: str) -> str:
    """Percent-decode a path exactly once, rejecting malformed encoding."""
    try:
        return unquote(raw, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise UnsafePathError(
            "Path contains invalid percent-encoding.", Reason.INVALID_ENCODING
        ) from exc


def split_checked(raw: str) -> list[str]:
    """Validate raw user input and return its safe path components."""
    if not raw:
        raise UnsafePathError("Path must not be empty.", Reason.EMPTY_PATH)
    if "\x00" in raw:
        raise UnsafePathError("Path contains a NUL byte.", Reason.NUL_BYTE)
    if ENCODED_NUL.search(raw):
        raise UnsafePathError("Path contains an encoded NUL byte.", Reason.NUL_BYTE)
    if ENCODED_TRAVERSAL.search(raw):
        raise UnsafePathError(
            "Path contains percent-encoded dots or separators.", Reason.ENCODED_TRAVERSAL
        )

    decoded = decode_once(raw)
    if not decoded:
        raise UnsafePathError("Path must not be empty.", Reason.EMPTY_PATH)
    if "\x00" in decoded:
        raise UnsafePathError("Path contains a NUL byte.", Reason.NUL_BYTE)

    # POSIX treats backslash as an ordinary filename character, but attackers
    # routinely use it as a separator to bypass POSIX-only filters.
    # Classify absolute/drive/UNC forms first so they report ABSOLUTE_PATH on
    # every platform. On POSIX, os.path.isabs() does not recognise Windows
    # forms, so the explicit prefix checks are required.
    if decoded.startswith(("/", "\\")) or WINDOWS_DRIVE.match(decoded) or os.path.isabs(decoded):
        raise UnsafePathError(
            "Absolute paths, drive letters, and UNC paths are not allowed.",
            Reason.ABSOLUTE_PATH,
        )

    # POSIX treats backslash as an ordinary filename character, but attackers
    # routinely use it as a separator to bypass POSIX-only filters.
    if os.name != "nt" and "\\" in decoded:
        raise UnsafePathError(
            "Backslash separators are not accepted on this platform.", Reason.TRAVERSAL
        )

    parts = [part for part in SEPARATORS.split(decoded) if part not in ("", ".")]
    for part in parts:
        if part == "..":
            raise UnsafePathError("Parent-directory traversal is not allowed.", Reason.TRAVERSAL)
        if WINDOWS_DRIVE.match(part):
            raise UnsafePathError(
                "Drive-qualified components are not allowed.", Reason.ABSOLUTE_PATH
            )

    if not parts:
        raise UnsafePathError("Path does not name anything.", Reason.EMPTY_PATH)
    return parts


def is_within(base: Path, candidate: Path) -> bool:
    """Return whether ``candidate`` is ``base`` or lives beneath it.

    Uses ``os.path.commonpath`` rather than a string prefix so that sibling
    directories with similar names never compare as nested.
    """
    try:
        return os.path.commonpath((str(base), str(candidate))) == str(base)
    except ValueError:
        # Raised by commonpath for paths on different Windows drives.
        return False
