"""safepath: stop path traversal before it reaches your filesystem.

The public API is intentionally small: :func:`safe_join` for one-off joins,
:class:`SafePathResolver` for repeated checks against one trusted directory,
:func:`sanitize_filename` for upload names, and :class:`UnsafePathError` with
stable reason codes.
"""

from __future__ import annotations

from .core import SafePathResolver, safe_join, sanitize_filename
from .errors import Reason, UnsafePathError

__version__ = "0.1.0"

__all__ = [
    "Reason",
    "SafePathResolver",
    "UnsafePathError",
    "__version__",
    "safe_join",
    "sanitize_filename",
]
