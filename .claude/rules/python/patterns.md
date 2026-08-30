---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Patterns

## Protocol (Duck Typing)

```python
from typing import Protocol

class Repository(Protocol):
    def find_by_id(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> dict: ...
```

## DTO Dataclasses

```python
@dataclass
class CreateUserRequest:
    name: str
    email: str
    age: int | None = None
```

## Idioms

- Context managers (`with`) for resources.
- Generators for lazy/memory-efficient iteration.
- Type hints over `Any`; `Self` for class-returning methods.