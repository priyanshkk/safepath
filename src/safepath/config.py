"""Configuration constants shared by the resolver, validator and CLI."""

from __future__ import annotations

import re
from typing import Final

ENV_BASE_VAR: Final = "SAFEPATH_BASE"

DEFAULT_REPLACEMENT: Final = "_"
MAX_FILENAME_LENGTH: Final = 255

SEPARATORS: Final = re.compile(r"[\\/]+")
ENCODED_TRAVERSAL: Final = re.compile(r"%2e|%2f|%5c|%00", re.IGNORECASE)
ENCODED_NUL: Final = re.compile(r"%00", re.IGNORECASE)
WINDOWS_DRIVE: Final = re.compile(r"^[A-Za-z]:")

RESERVED_FILENAMES: Final[frozenset[str]] = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
