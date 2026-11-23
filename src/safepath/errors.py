"""Exceptions raised by :mod:`safepath`.

Every rejection carries a stable, machine-readable ``reason`` code so callers can
log, count, or branch on the kind of unsafe input without parsing error text.
"""

from __future__ import annotations

from typing import Final


class Reason:
    """Canonical ``UnsafePathError.reason`` values.

    These are plain strings, not an enum, so they can be logged or serialised
    directly. New reasons may be added in minor releases; existing values will
    not change meaning.
    """

    ABSOLUTE_PATH: Final = "absolute_path"
    TRAVERSAL: Final = "traversal"
    OUTSIDE_BASE: Final = "outside_base"
    NUL_BYTE: Final = "nul_byte"
    ENCODED_TRAVERSAL: Final = "encoded_traversal"
    SYMLINK_ESCAPE: Final = "symlink_escape"
    EMPTY_PATH: Final = "empty_path"
    INVALID_ENCODING: Final = "invalid_encoding"


class UnsafePathError(ValueError):
    """Raised when a user-supplied path is rejected.

    Attributes:
        reason: A stable code from :class:`Reason`, such as ``"traversal"``.

    Example:
        >>> try:
        ...     safe_join("/srv/uploads", "../etc/passwd")
        ... except UnsafePathError as exc:
        ...     exc.reason
        'traversal'
    """

    def __init__(self, message: str, reason: str) -> None:
        """Initialise the error.

        Args:
            message: Human-readable explanation of the rejection.
            reason: Machine-readable reason code (see :class:`Reason`).
        """
        super().__init__(message)
        self.reason = reason

    def __repr__(self) -> str:
        """Return a developer-friendly representation including the reason."""
        return f"{type(self).__name__}({str(self)!r}, reason={self.reason!r})"


__all__ = ["Reason", "UnsafePathError"]
