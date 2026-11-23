# Usage guide

## Python API

### One-off joins

```python
from safepath import safe_join, UnsafePathError

try:
    path = safe_join("/srv/uploads", "reports", "2026.csv")
except UnsafePathError as exc:
    print(exc.reason)  # e.g. "traversal"
else:
    print(path)
```

Each component is checked independently, so a later absolute component cannot
discard the earlier ones. The base does not need to exist.

### Reusable resolver

```python
from safepath import SafePathResolver

resolver = SafePathResolver("/srv/uploads", strict=False)
resolver.is_safe("ok.txt")               # True
resolver.is_safe("../../etc/passwd")     # False
path = resolver.resolve("ok.txt")
```

Use `strict=True` (default) when the base and target must already exist.

### Upload filenames

```python
from safepath import sanitize_filename

sanitize_filename(r"..\..\CON.txt")    # '_CON.txt'
sanitize_filename("/etc/passwd")       # 'passwd'
sanitize_filename("a" * 300 + ".txt")  # 255 chars, extension preserved
```

### Reason codes

Always branch on `exc.reason`, not on the message text:

```python
from safepath import UnsafePathError, Reason

try:
    resolver.resolve(user_path)
except UnsafePathError as exc:
    if exc.reason == Reason.ABSOLUTE_PATH:
        reject("Absolute paths are not allowed")
    else:
        reject("Unsafe path")
```

## CLI

```console
$ safepath check /srv/uploads "reports/2026.csv"
$ safepath check /srv/uploads "../etc/passwd" --json
$ safepath sanitize "..\\..\\CON.txt"
```

| Flag | Meaning |
| --- | --- |
| `--json` | machine-readable result |
| `--allow-symlinks` | weaken containment (off by default) |

Exit codes: `0` accepted, `1` rejected, `2` bad usage.

## Environment

| Variable | Meaning |
| --- | --- |
| `SAFEPATH_BASE` | default trusted base for `safepath check` when BASE is omitted |

See `.env.example`. No secrets or API keys are used.

## Secure integration recipe

```python
from safepath import SafePathResolver

resolver = SafePathResolver("/srv/uploads")

def read_upload(user_path: str) -> bytes:
    safe = resolver.resolve(user_path)   # validate first
    return safe.read_bytes()             # then use ONLY the returned path
```

Never rebuild the path from the original user input after validation.
