# Contributing to safepath

Thanks for helping make file handling safer. Because this is a security
library, changes are reviewed more carefully than usual: a convenient shortcut
that weakens containment is a bug, not a feature.

## Development setup

```console
git clone https://github.com/priyanshu-kumar/safepath.git
cd safepath
python -m venv .venv
# Windows: .venv\Scripts\activate
# POSIX:   source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Required checks

Run these before opening a pull request:

```console
python -m ruff check .
python -m mypy src/safepath
python -m unittest discover -s tests -v
python -m pytest
```

The unittest suite must pass without installing the package. Tests use only the
standard library and insert `src` into `sys.path` themselves.

## Ground rules for code changes

1. **No new runtime dependencies.** The library must stay stdlib-only.
2. **Fail closed.** If a check cannot be completed, reject the path; never
   fall back to a permissive string operation.
3. **No prefix-based containment.** Use `os.path.commonpath` (or an equivalent
   component-wise comparison) on resolved paths.
4. **Decode at most once.** Never allow a second decode of user input.
5. **Add tests for every rejection case**, including the exact `reason` code.
   Tests should be cross-platform; use `tempfile` and skip only when a feature
   (such as symlinks) is genuinely unavailable.
6. **Public API changes need docs.** Update the README, docstrings, and
   CHANGELOG in the same pull request.
7. **Type hints and Google-style docstrings** are required on all public and
   internal functions. Keep lines within 100 characters.

## Reporting bugs

Include the Python version, operating system, the exact input, the expected
result, and the actual result. For security issues, follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.

## Commit style

Use short imperative subjects, for example `Reject encoded backslash separators`
or `Document strict resolver semantics`.
