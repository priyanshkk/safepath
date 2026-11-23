"""Test package setup.

Inserting ``src`` into ``sys.path`` here lets ``python -m unittest discover -s
tests`` work from the project root without installing the package first.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
