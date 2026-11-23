# Architecture

## Overview

safepath performs one job: convert an untrusted path into a canonical path that
is provably inside a trusted base directory, or reject it.

```
user input ──► structural checks ──► lexical containment ──► real-path containment ──► Path
```

Every stage rejects rather than repairs. A rejected input raises
`UnsafePathError` with a machine-readable `reason`.

## Package layout

```
src/safepath/
├── __init__.py        # public API
├── config.py          # regexes, reserved names, env variable name, defaults
├── errors.py          # UnsafePathError and Reason constants
├── cli.py             # `safepath check` and `safepath sanitize`
├── py.typed           # PEP 561 marker
├── core/
│   ├── __init__.py
│   └── resolver.py    # SafePathResolver, safe_join, sanitize_filename
└── utils/
    ├── __init__.py
    └── validation.py  # as_text, decode_once, split_checked, is_within
```

## Validation pipeline

1. **Type check** — `as_text` accepts only `str` or `os.PathLike[str]`; bytes
   must be decoded by the caller with an explicit encoding.
2. **Raw checks** — raw NUL bytes and percent-encoded dots, separators or NUL
   are rejected *before* decoding. Decoding happens exactly once so a second
   decode downstream cannot resurrect a traversal.
3. **Decoded checks** — absolute paths, Windows drive letters, UNC paths and
   `..` components are rejected. Backslashes are rejected outright on POSIX so
   they cannot be used to bypass POSIX-only filters.
4. **Lexical containment** — the joined path is checked with
   `os.path.commonpath`, never `str.startswith`.
5. **Real-path containment** — `Path.resolve(strict=False)` follows existing
   symlinks and junctions; if the resolved location leaves the real base, the
   path is rejected unless `allow_symlinks=True`.
6. **Existence (optional)** — `strict=True` additionally requires the base to
   be a directory and the target to exist.

## Why rejection over sanitisation

Silently rewriting `../etc/passwd` into `etcpasswd` hides an attack and makes
behaviour hard to reason about. Rejection forces the caller to handle hostile
input explicitly. `sanitize_filename` is the only "repair" API, and it is
documented as producing a single safe *filename*, not as a substitute for
containment checks.

## Cross-platform decisions

- Both `/` and `\\` are treated as separators during analysis.
- Drive-qualified components are rejected because `pathlib` would discard
  everything before them on Windows.
- `commonpath` is used because it correctly handles sibling directories and
  cross-drive comparisons on Windows.

## Threat model boundaries

The base directory is trusted; everything supplied by the user is not.
Out of scope: authorisation, TOCTOU races after validation, and bugs in the
caller's later I/O. See [SECURITY.md](https://github.com/priyanshkk/safepath/blob/main/SECURITY.md) and the README threat
model section.

## Testing approach

56 dependency-free `unittest` cases cover traversal forms, encoded payloads,
NUL bytes, Windows-style paths on POSIX, sanitisation, CLI exit codes and
symlink/junction escapes. On Windows, directory junctions are used where
`os.symlink` requires elevation; the escape path is still genuinely exercised.
