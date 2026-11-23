"""Command-line interface for :mod:`safepath`.

Examples:
    safepath check /srv/uploads "reports/2026.csv"
    safepath check /srv/uploads "../etc/passwd" --json
    safepath sanitize "..\\..\\CON.txt"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence

from . import __version__
from .config import ENV_BASE_VAR
from .core import SafePathResolver, sanitize_filename
from .errors import UnsafePathError


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        A configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="safepath",
        description="Validate untrusted paths and sanitise filenames.",
        epilog=f"BASE may also be supplied through the {ENV_BASE_VAR} environment variable.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check that a user path stays under BASE")
    check.add_argument("base", nargs="?", help="trusted base directory (or set SAFEPATH_BASE)")
    check.add_argument("user_path", help="untrusted relative path to validate")
    check.add_argument(
        "--allow-symlinks",
        action="store_true",
        help="allow symlinks that resolve outside BASE (unsafe; off by default)",
    )
    check.add_argument("--json", action="store_true", help="emit a machine-readable result")

    clean = commands.add_parser("sanitize", help="sanitise a single filename")
    clean.add_argument("name", help="untrusted filename (may contain directories)")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments to parse, or ``None`` to use ``sys.argv[1:]``.

    Returns:
        ``0`` on success, ``1`` when a path is rejected, and ``2`` for bad CLI
        usage (argparse raises ``SystemExit`` in that case).
    """
    args = _build_parser().parse_args(argv)

    if args.command == "sanitize":
        print(sanitize_filename(args.name))
        return 0

    if args.command == "check":
        base = args.base or os.getenv(ENV_BASE_VAR)
        if not base:
            print(f"error: provide BASE or set {ENV_BASE_VAR}", file=sys.stderr)
            return 2
        resolver = SafePathResolver(base, allow_symlinks=args.allow_symlinks, strict=False)
        try:
            resolved = resolver.resolve(args.user_path)
        except UnsafePathError as exc:
            if args.json:
                print(
                    json.dumps(
                        {"ok": False, "reason": exc.reason, "message": str(exc)},
                        ensure_ascii=False,
                    )
                )
            else:
                print(f"REJECTED [{exc.reason}]: {exc}", file=sys.stderr)
            return 1
        except (OSError, ValueError) as exc:
            if args.json:
                print(json.dumps({"ok": False, "reason": "error", "message": str(exc)}))
            else:
                print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps({"ok": True, "path": str(resolved)}, ensure_ascii=False))
        else:
            print(resolved)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
