---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Coding Style

## Standards

- Follow **PEP 8**.
- Type annotations on all function signatures.

## Immutability

- Prefer `@dataclass(frozen=True)` and `NamedTuple` for value objects.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
    email: str
```

## Formatting

- **black** for formatting, **isort** for import sorting, **ruff** for linting.

## Naming

- `snake_case` functions/vars, `PascalCase` classes, `UPPER_CASE` constants.