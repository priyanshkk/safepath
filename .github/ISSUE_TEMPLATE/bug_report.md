---
name: Bug report
about: Report a path that was handled incorrectly
title: "fix: "
labels: bug
assignees: ""
---

## Description

What happened, and what should have happened?

## Reproduction

```python
from safepath import SafePathResolver

resolver = SafePathResolver(BASE)
resolver.resolve("USER_PATH")
```

## Input and result

| | Value |
| --- | --- |
| Base directory | |
| User path | |
| Expected | |
| Actual | |
| Reason code (if rejected) | |

## Environment

- safepath version:
- Python version:
- OS and filesystem:
- Symlinks or junctions involved: yes / no

## Security note

If this is a security vulnerability, do **not** post details publicly. Follow
[SECURITY.md](../../SECURITY.md) instead.
