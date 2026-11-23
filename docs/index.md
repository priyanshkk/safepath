# safepath

A dependency-free Python library that turns untrusted user paths into paths
that are provably inside a trusted directory.

```python
from safepath import SafePathResolver

resolver = SafePathResolver("/srv/uploads")
resolver.resolve("reports/2026.csv")   # safe
resolver.resolve("../etc/passwd")      # UnsafePathError(traversal)
```

Start with the [usage guide](usage.md), then read the
[architecture](architecture.md) for the validation pipeline and design
decisions.
