# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [0.1.0] - 2026-11-23

### Added

- `safe_join(base, *parts)` for one-shot, component-wise safe joins.
- `SafePathResolver` with `resolve()`, `is_safe()`, and a `base` property, plus
  `strict` and `allow_symlinks` options.
- `sanitize_filename()` with Windows reserved-name neutralisation and
  extension-preserving truncation.
- `UnsafePathError` with stable reason codes exposed through `Reason`.
- `safepath check` and `safepath sanitize` CLI commands, including JSON output.
- Cross-platform tests: reject traversal, absolute/drive/UNC paths, encoded
  traversal, NUL bytes, backslash separators on POSIX, and symlink escapes.
- CI matrix for Python 3.10–3.13 and a Windows smoke job.

[Unreleased]: https://github.com/priyanshu-kumar/safepath/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/priyanshu-kumar/safepath/releases/tag/v0.1.0
