# safepath

[![Tests](https://github.com/priyanshkk/safepath/actions/workflows/tests.yml/badge.svg)](https://github.com/priyanshkk/safepath/actions/workflows/tests.yml)
[![Linter](https://github.com/priyanshkk/safepath/actions/workflows/linter.yml/badge.svg)](https://github.com/priyanshkk/safepath/actions/workflows/linter.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests: 56 passing](https://img.shields.io/badge/tests-56%20passing-brightgreen.svg)](#development)
[![Typing: strict](https://img.shields.io/badge/typing-strict-blue.svg)](pyproject.toml)
[![Runtime deps: 0](https://img.shields.io/badge/runtime%20deps-0-brightgreen.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Stop path traversal before it reaches your filesystem.**

`safepath` is a small, dependency-free security library for the boring but
dangerous job every file-serving app has: turning a path supplied by a user into
a path that is *provably* inside a directory you trust.

```python
from safepath import SafePathResolver

resolver = SafePathResolver("/srv/uploads")
path = resolver.resolve("reports/2026.csv")  # /srv/uploads/reports/2026.csv
resolver.resolve("../etc/passwd")            # raises UnsafePathError(traversal)
```

## Why it exists

Joining user input with `Path(base) / user_path` is not validation. On most
platforms an absolute later component silently **discards the base**, `..`
walks out of it, and symlinks can redirect a path that looks harmless into a
completely different tree. Percent-encoding adds another layer: `..%2f` is
invisible to many filters.

Common real-world failures this library prevents:

| Input | Naive result | safepath |
| --- | --- | --- |
| `../../etc/passwd` | reads `/etc/passwd` | `UnsafePathError(traversal)` |
| `/etc/passwd` | replaces the base entirely | `UnsafePathError(absolute_path)` |
| `C:\Windows\win.ini` | drive escape on Windows | `UnsafePathError(absolute_path)` |
| `\\server\share\file` | UNC escape on Windows | `UnsafePathError(absolute_path)` |
| `..\..\secret` on POSIX | treated as a literal name, bypassing POSIX checks | `UnsafePathError(traversal)` |
| `%2e%2e/secret` | decoded by the web framework *after* validation | `UnsafePathError(encoded_traversal)` |
| `uploads/link/secret` where `link` → `/etc` | follows the symlink outside | `UnsafePathError(symlink_escape)` |
| `file\x00.txt` | truncation in lower-level APIs | `UnsafePathError(nul_byte)` |

## Threat model

**Trusted:** the base directory you pass in. If the base itself is a symlink, its
real location is treated as the trusted root; files genuinely inside it are
allowed.

**Untrusted:** every component supplied by the user, including its encoding,
separators, and any symlinks encountered while resolving it.

**Out of scope:** the caller's own bugs after validation (for example following
a symlink again, or using a different base for the actual open), TOCTOU races
where an attacker replaces a directory between the check and the open, and
authorisation decisions (who may read which file).

### Design rules

- Reject, do not silently rewrite, dangerous user paths.
- Decode percent-encoding **at most once**, and reject encoded dots/separators
  outright so a second decode downstream cannot resurrect a traversal.
- Treat both `/` and `\` as separators for analysis on every platform. On POSIX
  a backslash is rejected entirely, so it can never be used to bypass a filter.
- Verify containment with `os.path.commonpath` on fully resolved paths — never
  with `str.startswith`.
- Resolve symlinks before deciding; `is_safe()` performs the same symlink check.

## Install

```console
python -m pip install safepath
```

No runtime dependencies. Python 3.10+, Linux, macOS, and Windows are supported.

## Quickstart

### One-off join

```python
from safepath import safe_join, UnsafePathError

try:
    path = safe_join("/srv/uploads", "reports", "2026.csv")
except UnsafePathError as exc:
    print(exc.reason)  # e.g. "traversal"
else:
    print(path)        # /srv/uploads/reports/2026.csv
```

`safe_join` does not require the base to exist; use it to build destinations for
files you are about to create.

### Reusable resolver

```python
from safepath import SafePathResolver

resolver = SafePathResolver("/srv/uploads")  # strict=True by default

resolver.base                       # Path('/srv/uploads')
resolver.is_safe("ok.txt")          # True
resolver.is_safe("../../etc/passwd")  # False; never follows the escape
resolver.resolve("ok.txt")          # Path('/srv/uploads/ok.txt')
```

Use `strict=False` when the target may not exist yet:

```python
resolver = SafePathResolver("/srv/uploads", strict=False)
resolver.resolve("new-upload.bin")
```

`strict=True` means the base must be a directory and the resolved path must
exist; otherwise `FileNotFoundError` is raised. `is_safe()` ignores existence,
so `"new-upload.bin"` is safe under either setting.

### Upload filenames

```python
from safepath import sanitize_filename

sanitize_filename(r"..\..\CON.txt")     # '_CON.txt'
sanitize_filename("/etc/passwd")        # 'passwd'
sanitize_filename("report\x00.txt")     # 'report_.txt'
sanitize_filename("a" * 300 + ".txt")   # 255 chars, extension preserved
```

Windows reserved names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–
`LPT9`), NUL and control characters, directory components, and trailing dots
and spaces are all removed or neutralised.

### CLI

Real output from a local run (`DEMO_BASE` is a temporary directory):

```console
$ safepath check "$DEMO_BASE" "reports/2026.csv"
C:\Users\...\Temp\safepath-demo\reports\2026.csv

$ safepath check "$DEMO_BASE" "../etc/passwd"
REJECTED [traversal]: Parent-directory traversal is not allowed.

$ safepath sanitize "..\..\CON.txt"
_CON.txt

$ export SAFEPATH_BASE="$DEMO_BASE"
$ safepath check "ok.txt"
C:\Users\...\Temp\safepath-demo\ok.txt
```

Exit codes: `0` accepted, `1` rejected, `2` bad usage. The check command never
requires the target to exist and never allows symlink escapes.

## API

| Symbol | Description |
| --- | --- |
| `safe_join(base, *parts) -> Path` | Validate each component and return the canonical path inside `base`. |
| `SafePathResolver(base, *, allow_symlinks=False, strict=True)` | Reusable resolver for one trusted base. |
| `.resolve(user_path) -> Path` | Return the canonical absolute path or raise. |
| `.is_safe(user_path) -> bool` | Non-raising check; still detects symlink escapes. |
| `.base -> Path` | Absolute base directory used for containment. |
| `sanitize_filename(name, *, replacement="_", max_length=255) -> str` | Produce one safe filename. |
| `UnsafePathError` | `ValueError` subclass with a `.reason` code. |
| `Reason` | Constants for every reason code. |

### Reason codes

| Reason | Meaning |
| --- | --- |
| `absolute_path` | Absolute path, drive letter (`C:`), drive-relative path, or UNC path. |
| `traversal` | A `..` component, or a backslash separator on POSIX. |
| `outside_base` | Lexical containment invariant failed (defence in depth). |
| `nul_byte` | Raw or percent-encoded NUL byte. |
| `encoded_traversal` | Percent-encoded dot or separator (`%2e`, `%2f`, `%5c`). |
| `symlink_escape` | Resolved location left the base through a symlink or junction. |
| `empty_path` | Empty input, or input containing no usable component. |
| `invalid_encoding` | Malformed percent-encoded UTF-8. |

## Security notes

- **Keep the base trusted and narrow.** A base of `/` makes containment
  meaningless. Prefer a dedicated directory per user or tenant.
- **Use the returned path for the actual I/O.** Do not reconstruct a path from
  the original user input after validation.
- **TOCTOU:** an attacker with write access to the directory tree can swap a
  symlink between `resolve()` and `open()`. On POSIX, open with `O_NOFOLLOW`
  where practical, keep the upload tree unwritable by untrusted processes, and
  re-check immediately before use.
- **`allow_symlinks=True` disables the symlink escape guarantee.** It exists for
  layouts that intentionally link to shared, trusted storage; never enable it
  for arbitrary user input.
- **Encoded input is rejected, not repaired.** A literal filename containing
  `%2e` or `%2f` will be refused; choose a different name. Double-encoded
  input (`%252e%252e`) is decoded only once and cannot become a traversal.
- **Case-insensitive filesystems are handled** through resolved paths and
  `commonpath`, but casing can still affect which file you open; canonicalise
  before storing filenames.
- **Sanitisation is not validation.** `sanitize_filename` produces a safe
  single name; it is not a substitute for containment checks when the input can
  contain directories.
- Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Project structure

```
safepath/
├── .github/
│   ├── ISSUE_TEMPLATE/          # bug report + feature request
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/               # tests, linter, docs, overall CI
├── docs/                        # index, architecture and usage guides
├── scripts/                     # setup.ps1 / setup.sh
├── src/safepath/
│   ├── __init__.py              # public API
│   ├── config.py                # constants and env variable name
│   ├── errors.py                # UnsafePathError and Reason codes
│   ├── cli.py                   # command-line interface
│   ├── core/                    # resolver, safe_join, sanitize_filename
│   └── utils/                   # input validation primitives
├── tests/                       # 56 unittest cases
├── .env.example
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Configuration

| Variable | Meaning |
| --- | --- |
| `SAFEPATH_BASE` | Default trusted base for `safepath check` when BASE is omitted |

No API keys, tokens or database URLs are used. See `.env.example`.

## Development

```console
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src/safepath
python -m pytest
python -m unittest discover -s tests -v
```

The unittest suite is the authoritative, dependency-free check: it inserts
`src` into `sys.path` and runs from the project root without installing the
package. CI runs the full toolchain on Python 3.10–3.13 plus a Windows smoke job.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Priyanshu Kumar.
