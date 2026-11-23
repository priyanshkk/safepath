# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |

## Reporting a vulnerability

Please **do not** open a public issue for a security vulnerability.

Use GitHub's private vulnerability reporting on the repository
(**Security → Report a vulnerability**), or email the maintainer directly if
private reporting is unavailable. Include:

- a minimal proof of concept (input path, base directory, filesystem layout);
- the platform, Python version, and `safepath` version;
- the impact you believe is possible (for example reading a file outside base).

You should receive an acknowledgement within 7 days. We will work with you on a
fix, add a regression test, and coordinate disclosure once a release is
available. Please give us a reasonable window before public disclosure.

## What is in scope

- Any user path accepted by `safe_join()` or `SafePathResolver` that resolves
  outside the configured base when `allow_symlinks=False`.
- Bypasses involving separators, encoding, NUL bytes, drive letters, UNC paths,
  reserved names, or symlinks/junctions.
- `sanitize_filename()` output containing path separators, control characters,
  or an unneutralised Windows reserved name.

## What is out of scope

- Misuse of `allow_symlinks=True`, which explicitly disables the symlink escape
  guarantee.
- Time-of-check/time-of-use races where an attacker can modify the directory
  tree between validation and file access (see the README's security notes).
- Vulnerabilities in callers that discard the validated path and reconstruct a
  new one from raw user input.
- Social engineering, compromised hosts, or filesystem bugs outside this
  library's control.
