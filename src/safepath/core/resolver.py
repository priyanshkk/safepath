"""Path containment and filename sanitisation primitives.

The module is deliberately dependency-free and works the same way on POSIX and
Windows. User input is treated as hostile until it has passed every check.
"""

from __future__ import annotations

import errno
import os
import unicodedata
from collections.abc import Sequence
from pathlib import Path

from ..config import (
    DEFAULT_REPLACEMENT,
    MAX_FILENAME_LENGTH,
    RESERVED_FILENAMES,
    SEPARATORS,
)
from ..errors import Reason, UnsafePathError
from ..utils.validation import as_text, is_within, split_checked


class SafePathResolver:
    """Resolve untrusted relative paths underneath a trusted base directory.

    Attacks are rejected before any resolved path is returned. Unless
    ``allow_symlinks=True``, a path is rejected when its real location leaves the
    base directory, including escapes through intermediate symlinks.

    Args:
        base: The trusted directory that all user paths are confined to.
        allow_symlinks: Permit symlinks whose target resolves outside ``base``.
            Off by default; enabling it weakens the containment guarantee.
        strict: Require the resolved path (and base directory) to exist. Set to
            ``False`` when constructing paths for files that do not exist yet.

    Example:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     resolver = SafePathResolver(tmp, strict=False)
        ...     resolver.is_safe("../secrets.txt")
        False
    """

    def __init__(
        self,
        base: str | os.PathLike[str],
        *,
        allow_symlinks: bool = False,
        strict: bool = True,
    ) -> None:
        self._base = Path(as_text(base)).absolute()
        self._allow_symlinks = bool(allow_symlinks)
        self._strict = bool(strict)

    @property
    def base(self) -> Path:
        """Return the absolute base directory used for containment checks."""
        return self._base

    @property
    def allow_symlinks(self) -> bool:
        """Return whether symlinks may resolve outside the base directory."""
        return self._allow_symlinks

    @property
    def strict(self) -> bool:
        """Return whether resolved paths must already exist."""
        return self._strict

    def resolve(self, user_path: str | os.PathLike[str]) -> Path:
        """Validate ``user_path`` and return its canonical absolute path.

        Args:
            user_path: Relative path supplied by an untrusted party.

        Returns:
            The resolved, absolute path, guaranteed to be inside the base
            directory unless ``allow_symlinks=True`` and a symlink escapes.

        Raises:
            UnsafePathError: If the path is unsafe.
            FileNotFoundError: If ``strict`` is true and the path does not exist.
            TypeError: If ``user_path`` is not a text path.
        """
        return self._check(user_path, require_existence=self._strict)

    def is_safe(self, user_path: str | os.PathLike[str]) -> bool:
        """Return whether ``user_path`` passes all structural and symlink checks.

        Existence is deliberately not required, so a name for a file that is
        about to be created is still considered safe. Symlinks are checked
        before this method returns ``True``.

        Args:
            user_path: Relative path supplied by an untrusted party.

        Returns:
            ``True`` if the path would resolve safely, ``False`` otherwise.
        """
        try:
            self._check(user_path, require_existence=False)
        except (UnsafePathError, OSError, ValueError):
            return False
        return True

    def _check(self, user_path: str | os.PathLike[str], *, require_existence: bool) -> Path:
        """Run the full validation pipeline.

        Args:
            user_path: Untrusted path text.
            require_existence: Whether a missing target should be an error.

        Returns:
            The canonical resolved path.

        Raises:
            UnsafePathError: If the path is unsafe.
            FileNotFoundError: If existence is required and the path is missing.
        """
        parts = split_checked(as_text(user_path))
        return self._resolve_parts(parts, require_existence=require_existence)

    def _resolve_parts(self, parts: Sequence[str], *, require_existence: bool) -> Path:
        """Join already-validated parts, then verify real filesystem containment.

        Args:
            parts: Safe path components produced by :func:`_split_checked`.
            require_existence: Whether a missing target should be an error.

        Returns:
            The canonical resolved path.

        Raises:
            UnsafePathError: If lexical or real containment fails.
            FileNotFoundError: If existence is required and the path is missing.
        """
        if not parts:
            raise UnsafePathError("Path must not be empty.", Reason.EMPTY_PATH)

        lexical = self._base.joinpath(*parts)
        if not is_within(self._base, lexical):
            raise UnsafePathError("Path escapes the base directory.", Reason.OUTSIDE_BASE)

        # resolve(strict=False) still follows every symlink component that
        # exists, so escapes are detected even for not-yet-created files.
        base_real = self._base.resolve(strict=False)
        candidate_real = lexical.resolve(strict=False)
        if not is_within(base_real, candidate_real) and not self._allow_symlinks:
            raise UnsafePathError(
                "Path resolves outside the base directory through a symlink.",
                Reason.SYMLINK_ESCAPE,
            )

        if require_existence and not (base_real.is_dir() and candidate_real.exists()):
            raise FileNotFoundError(
                errno.ENOENT,
                "Base directory or resolved path does not exist",
                str(candidate_real),
            )
        return candidate_real


def safe_join(base: str | os.PathLike[str], *parts: str) -> Path:
    """Join path components to ``base`` and reject anything that escapes it.

    Each component is validated independently, so a later absolute component
    (for example ``safe_join(base, "uploads", "/etc/passwd")``) cannot discard
    the ones before it.

    The base directory is not required to exist: this function is intended for
    building destination paths for new files. Set ``strict=True`` on
    :class:`SafePathResolver` if existence must be verified.

    Args:
        base: Trusted directory that the result must stay under.
        *parts: Untrusted relative path components.

    Returns:
        The canonical absolute path inside ``base``.

    Raises:
        UnsafePathError: If any part is unsafe.
        TypeError: If a part is not a text path.

    Example:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     safe_join(tmp, "reports", "2026.csv").parent.name
        'reports'
    """
    if not parts:
        raise UnsafePathError("At least one path component is required.", Reason.EMPTY_PATH)

    segments: list[str] = []
    for part in parts:
        text = as_text(part)
        # "." and "./" are harmless no-ops, but a truly empty part is not.
        if text and all(segment == "." for segment in SEPARATORS.split(text)):
            continue
        segments.extend(split_checked(text))
    return SafePathResolver(base, strict=False)._resolve_parts(
        segments, require_existence=False
    )


def sanitize_filename(
    name: str,
    *,
    replacement: str = DEFAULT_REPLACEMENT,
    max_length: int = MAX_FILENAME_LENGTH,
) -> str:
    """Turn untrusted text into a single safe, portable filename.

    The function removes directory components, NUL and other control
    characters, neutralises Windows reserved device names, and trims trailing
    dots and spaces. If truncation is needed, the file extension is preserved.

    Args:
        name: Untrusted text, which may contain a full path.
        replacement: Substitution for removed characters. Must not contain a
            path separator, NUL, or control characters.
        max_length: Maximum number of characters in the result. Must be positive.

    Returns:
        A filename with no path components and no dangerous characters.

    Raises:
        TypeError: If ``name`` or ``replacement`` is not a string.
        ValueError: If ``replacement`` or ``max_length`` is invalid.

    Example:
        >>> sanitize_filename(r"..\\..\\CON.txt")
        '_CON.txt'
    """
    if not isinstance(name, str):
        raise TypeError("name must be str")
    if not isinstance(replacement, str):
        raise TypeError("replacement must be str")
    if any(char in replacement for char in ("/", "\\", "\x00")) or any(
        unicodedata.category(char) == "Cc" for char in replacement
    ):
        raise ValueError("replacement must not contain separators, NUL, or control characters")
    if isinstance(max_length, bool) or not isinstance(max_length, int) or max_length < 1:
        raise ValueError("max_length must be a positive integer")

    filename = SEPARATORS.split(name)[-1]
    cleaned = "".join(
        replacement if unicodedata.category(char) == "Cc" else char for char in filename
    )
    cleaned = cleaned.rstrip(". ")
    if not cleaned:
        return (replacement or "unnamed")[:max_length]

    stem, extension = os.path.splitext(cleaned)
    stem = stem.rstrip(". ")
    if stem.upper() in RESERVED_FILENAMES:
        stem = f"{replacement}{stem}"

    result = stem + extension
    if len(result) > max_length:
        if len(extension) >= max_length:
            result = result[:max_length]
        else:
            result = stem[: max_length - len(extension)].rstrip(". ") + extension

    return result or (replacement or "unnamed")[:max_length]


__all__ = ["SafePathResolver", "safe_join", "sanitize_filename"]
